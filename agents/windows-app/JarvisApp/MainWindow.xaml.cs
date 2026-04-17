using System.Diagnostics;
using System.Globalization;
using System.Net.WebSockets;
using System.Speech.Recognition;
using System.Speech.Synthesis;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shapes;
using System.Windows.Threading;

namespace JarvisApp;

public partial class MainWindow : Window
{
    private ClientWebSocket? _ws;
    private bool _connected;
    private bool _listening;
    private readonly string _deviceId;
    private readonly string _brainWs;
    private readonly CancellationTokenSource _cts = new();

    // Voice
    private SpeechRecognitionEngine? _recognizer;
    private SpeechSynthesizer? _synth;
    private bool _sttReady;
    private bool _ttsReady;
    private TaskCompletionSource<string?>? _listenTcs;

    public MainWindow()
    {
        InitializeComponent();

        _deviceId = Environment.GetEnvironmentVariable("JARVIS_DEVICE_ID") ?? "windows-native";
        _brainWs = Environment.GetEnvironmentVariable("JARVIS_BRAIN_WS") ?? "ws://localhost:8400/ws";

        Loaded += OnLoaded;

        // Ctrl+Space shortcut
        InputBindings.Add(new KeyBinding(
            new RelayCommand(_ => MicBtn_Click(null, null)),
            Key.Space, ModifierKeys.Control));
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        InitVoice();
        AddSystemMessage("Connecting to brain...");
        await ConnectLoop();
    }

    // ═══════════════════════════════════════════
    //  Voice
    // ═══════════════════════════════════════════

    private void InitVoice()
    {
        // TTS
        try
        {
            _synth = new SpeechSynthesizer();
            _synth.SetOutputToDefaultAudioDevice();
            _synth.Rate = 1;
            // Pick a good voice
            foreach (var v in _synth.GetInstalledVoices())
            {
                if (v.VoiceInfo.Name.Contains("David", StringComparison.OrdinalIgnoreCase) ||
                    v.VoiceInfo.Name.Contains("Mark", StringComparison.OrdinalIgnoreCase))
                {
                    _synth.SelectVoice(v.VoiceInfo.Name);
                    break;
                }
            }
            _ttsReady = true;
        }
        catch { _ttsReady = false; }

        // STT
        try
        {
            _recognizer = new SpeechRecognitionEngine(new CultureInfo("en-US"));
            _recognizer.LoadGrammar(new DictationGrammar());
            _recognizer.SetInputToDefaultAudioDevice();
            _recognizer.SpeechRecognized += (s, args) =>
            {
                _listenTcs?.TrySetResult(args.Result.Text);
            };
            _recognizer.RecognizeCompleted += (s, args) =>
            {
                _listenTcs?.TrySetResult(null);
            };
            _sttReady = true;
        }
        catch { _sttReady = false; }

        Dispatcher.Invoke(() =>
        {
            VoiceBadge.Text = _sttReady ? "Voice ON" : "Voice OFF";
            VoiceBadge.Foreground = _sttReady
                ? (Brush)FindResource("Green")
                : (Brush)FindResource("Red");

            if (!_sttReady) MicBtn.Visibility = Visibility.Collapsed;
        });
    }

    private async Task<string?> ListenAsync()
    {
        if (!_sttReady || _recognizer == null) return null;
        _listenTcs = new TaskCompletionSource<string?>();

        try
        {
            _recognizer.RecognizeAsync(RecognizeMode.Single);
            var result = await Task.WhenAny(_listenTcs.Task, Task.Delay(10000));
            if (result != _listenTcs.Task)
            {
                _recognizer.RecognizeAsyncCancel();
                return null;
            }
            return await _listenTcs.Task;
        }
        catch
        {
            return null;
        }
    }

    private void Speak(string text)
    {
        if (!_ttsReady || _synth == null) return;
        Task.Run(() =>
        {
            try { _synth.Speak(text); } catch { }
        });
    }

    // ═══════════════════════════════════════════
    //  WebSocket
    // ═══════════════════════════════════════════

    private async Task ConnectLoop()
    {
        int delay = 1000;
        while (!_cts.IsCancellationRequested)
        {
            try
            {
                _ws = new ClientWebSocket();
                var token = Environment.GetEnvironmentVariable("JARVIS_AGENT_TOKEN");
                if (!string.IsNullOrEmpty(token))
                    _ws.Options.SetRequestHeader("Authorization", $"Bearer {token}");

                await _ws.ConnectAsync(new Uri(_brainWs), _cts.Token);

                // Send agent_connect
                var connectMsg = JsonSerializer.Serialize(new
                {
                    @event = "agent_connect",
                    device_id = _deviceId,
                    platform = "windows",
                    capabilities = new[] { "os_control", "apps", "files", "browser", "terminal", "clipboard", "system", "voice" }
                });
                await WsSend(connectMsg);

                // Read ack
                var ack = await WsReceive();
                if (ack != null && ack.RootElement.GetProperty("event").GetString() == "connected")
                {
                    _connected = true;
                    delay = 1000;
                    Dispatcher.Invoke(() =>
                    {
                        StatusDot.Fill = (Brush)FindResource("Green");
                        StatusText.Text = "Connected";
                        AddSystemMessage("Brain connected. Ready.");
                    });
                }

                // Receive loop
                while (_ws.State == WebSocketState.Open && !_cts.IsCancellationRequested)
                {
                    var msg = await WsReceive();
                    if (msg != null) HandleMessage(msg);
                }
            }
            catch { }

            _connected = false;
            Dispatcher.Invoke(() =>
            {
                StatusDot.Fill = (Brush)FindResource("Red");
                StatusText.Text = "Disconnected";
            });
            await Task.Delay(delay, CancellationToken.None);
            delay = Math.Min(delay * 2, 30000);
        }
    }

    private async Task WsSend(string text)
    {
        if (_ws?.State != WebSocketState.Open) return;
        var bytes = Encoding.UTF8.GetBytes(text);
        await _ws.SendAsync(bytes, WebSocketMessageType.Text, true, _cts.Token);
    }

    private async Task<JsonDocument?> WsReceive()
    {
        var buf = new byte[65536];
        var sb = new StringBuilder();
        WebSocketReceiveResult result;
        do
        {
            result = await _ws!.ReceiveAsync(buf, _cts.Token);
            sb.Append(Encoding.UTF8.GetString(buf, 0, result.Count));
        } while (!result.EndOfMessage);

        if (result.MessageType == WebSocketMessageType.Close) return null;
        return JsonDocument.Parse(sb.ToString());
    }

    private void HandleMessage(JsonDocument doc)
    {
        var ev = doc.RootElement.GetProperty("event").GetString();

        if (ev == "response")
        {
            if (doc.RootElement.TryGetProperty("text", out var textProp))
            {
                var text = textProp.GetString() ?? "";
                if (!string.IsNullOrWhiteSpace(text))
                {
                    Dispatcher.Invoke(() => AddMessage("jarvis", text));
                    if (doc.RootElement.TryGetProperty("tts", out var ttsProp) && ttsProp.GetBoolean())
                        Speak(text);
                }
            }
            if (doc.RootElement.TryGetProperty("actions", out var actionsProp))
            {
                foreach (var act in actionsProp.EnumerateArray())
                    ExecuteAction(act);
            }
        }
        else if (ev == "notification")
        {
            var msg = doc.RootElement.TryGetProperty("message", out var mp) ? mp.GetString() : "";
            Dispatcher.Invoke(() => AddSystemMessage(msg ?? ""));
        }
    }

    private async Task SendToBrain(string text)
    {
        if (!_connected) return;
        var msg = JsonSerializer.Serialize(new
        {
            @event = "user_input",
            device_id = _deviceId,
            text
        });
        await WsSend(msg);
    }

    // ═══════════════════════════════════════════
    //  Actions
    // ═══════════════════════════════════════════

    private void ExecuteAction(JsonElement act)
    {
        var type = act.GetProperty("type").GetString() ?? "";
        var target = act.TryGetProperty("target", out var tp) ? tp.GetString() ?? "" : "";

        Task.Run(() =>
        {
            try
            {
                if (type == "open_app")
                    Process.Start(new ProcessStartInfo { FileName = target, UseShellExecute = true });
                else if (type == "open_url")
                    Process.Start(new ProcessStartInfo { FileName = target.StartsWith("http") ? target : $"https://{target}", UseShellExecute = true });
                else if (type == "search")
                    Process.Start(new ProcessStartInfo { FileName = $"https://www.google.com/search?q={Uri.EscapeDataString(target)}", UseShellExecute = true });

                Dispatcher.Invoke(() => AddSystemMessage($"Done: {type} {target}"));
            }
            catch (Exception ex)
            {
                Dispatcher.Invoke(() => AddSystemMessage($"Failed: {type} -- {ex.Message}"));
            }
        });
    }

    // ═══════════════════════════════════════════
    //  UI Handlers
    // ═══════════════════════════════════════════

    private async void SendBtn_Click(object? sender, RoutedEventArgs? e)
    {
        var text = InputBox.Text.Trim();
        if (string.IsNullOrEmpty(text)) return;
        InputBox.Text = "";
        AddMessage("user", text);
        ShowTyping(true);
        await SendToBrain(text);
    }

    private void InputBox_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter) SendBtn_Click(null, null);
    }

    private async void MicBtn_Click(object? sender, RoutedEventArgs? e)
    {
        if (_listening || !_sttReady) return;
        _listening = true;
        MicBtn.Content = "🔴";
        MicBtn.Background = (Brush)FindResource("Red");
        AddSystemMessage("Listening... speak now");

        var text = await Task.Run(ListenAsync);

        _listening = false;
        Dispatcher.Invoke(() =>
        {
            MicBtn.Content = "🎤";
            MicBtn.Background = (Brush)FindResource("Surface");
        });

        if (!string.IsNullOrWhiteSpace(text))
        {
            AddMessage("user", text);
            ShowTyping(true);
            await SendToBrain(text);
        }
        else
        {
            AddSystemMessage("Didn't catch that. Try again.");
        }
    }

    private void Window_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        _cts.Cancel();
        _synth?.Dispose();
        _recognizer?.Dispose();
        _ws?.Dispose();
    }

    // ═══════════════════════════════════════════
    //  Chat UI Builders
    // ═══════════════════════════════════════════

    private void AddMessage(string role, string text)
    {
        ShowTyping(false);
        bool isUser = role == "user";
        var time = DateTime.Now.ToString("HH:mm");

        // Container
        var container = new Border
        {
            Margin = new Thickness(0, 4, 0, 4),
            HorizontalAlignment = isUser ? HorizontalAlignment.Right : HorizontalAlignment.Left,
            MaxWidth = 380,
        };

        var row = new StackPanel { Orientation = Orientation.Horizontal };
        if (!isUser) row.FlowDirection = FlowDirection.LeftToRight;

        // Avatar
        var avatar = new Border
        {
            Width = 32, Height = 32, CornerRadius = new CornerRadius(8),
            Margin = isUser ? new Thickness(10, 0, 0, 0) : new Thickness(0, 0, 10, 0),
            VerticalAlignment = VerticalAlignment.Top,
            Child = new TextBlock
            {
                Text = isUser ? "U" : "J",
                Foreground = Brushes.White,
                FontSize = 14, FontWeight = FontWeights.SemiBold,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
            }
        };
        if (isUser)
            avatar.Background = (Brush)FindResource("Surface");
        else
        {
            avatar.Background = new LinearGradientBrush(
                Color.FromRgb(99, 102, 241), Color.FromRgb(79, 70, 229), 45);
        }

        // Bubble
        var bubble = new Border
        {
            CornerRadius = new CornerRadius(16, 16, isUser ? 4 : 16, isUser ? 16 : 4),
            Padding = new Thickness(14, 10, 14, 10),
            Background = isUser ? (Brush)FindResource("UserBubble") : (Brush)FindResource("JarvisBubble"),
            BorderBrush = isUser ? (Brush)FindResource("Border") : (Brush)FindResource("JarvisBorder"),
            BorderThickness = new Thickness(1),
        };

        var inner = new StackPanel();

        // Header
        var header = new DockPanel { Margin = new Thickness(0, 0, 0, 4) };
        header.Children.Add(new TextBlock
        {
            Text = isUser ? "You" : "Jarvis",
            FontSize = 11, FontWeight = FontWeights.SemiBold,
            Foreground = isUser ? (Brush)FindResource("TextSecondary") : (Brush)FindResource("Accent"),
        });
        var timeBlock = new TextBlock
        {
            Text = time, FontSize = 10,
            Foreground = (Brush)FindResource("TextDim"),
            Margin = new Thickness(12, 0, 0, 0),
        };
        DockPanel.SetDock(timeBlock, Dock.Right);
        header.Children.Insert(0, timeBlock);
        inner.Children.Add(header);

        // Text
        inner.Children.Add(new TextBlock
        {
            Text = text,
            FontSize = 13, LineHeight = 20,
            Foreground = (Brush)FindResource("TextPrimary"),
            TextWrapping = TextWrapping.Wrap,
        });

        bubble.Child = inner;

        if (isUser)
        {
            row.Children.Add(bubble);
            row.Children.Add(avatar);
        }
        else
        {
            row.Children.Add(avatar);
            row.Children.Add(bubble);
        }

        container.Child = row;

        // Fade-in animation
        container.Opacity = 0;
        ChatPanel.Children.Add(container);
        var anim = new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(200));
        container.BeginAnimation(OpacityProperty, anim);

        ScrollToBottom();
    }

    private void AddSystemMessage(string text)
    {
        ShowTyping(false);
        var tb = new TextBlock
        {
            Text = text,
            FontSize = 11,
            Foreground = (Brush)FindResource("TextDim"),
            HorizontalAlignment = HorizontalAlignment.Center,
            Margin = new Thickness(0, 8, 0, 4),
        };
        ChatPanel.Children.Add(tb);
        ScrollToBottom();
    }

    private TextBlock? _typingIndicator;

    private void ShowTyping(bool show)
    {
        if (show && _typingIndicator == null)
        {
            _typingIndicator = new TextBlock
            {
                Text = "Jarvis is thinking...",
                FontSize = 11, FontStyle = FontStyles.Italic,
                Foreground = (Brush)FindResource("TextDim"),
                Margin = new Thickness(44, 6, 0, 6),
            };
            ChatPanel.Children.Add(_typingIndicator);
            ScrollToBottom();
        }
        else if (!show && _typingIndicator != null)
        {
            ChatPanel.Children.Remove(_typingIndicator);
            _typingIndicator = null;
        }
    }

    private void ScrollToBottom()
    {
        Dispatcher.InvokeAsync(() => ChatScroll.ScrollToEnd(), DispatcherPriority.Background);
    }
}

// Simple relay command for key bindings
public class RelayCommand : ICommand
{
    private readonly Action<object?> _execute;
    public RelayCommand(Action<object?> execute) => _execute = execute;
    public event EventHandler? CanExecuteChanged;
    public bool CanExecute(object? parameter) => true;
    public void Execute(object? parameter) => _execute(parameter);
}
