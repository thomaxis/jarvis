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
using System.Windows.Media.Effects;
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

    private SpeechRecognitionEngine? _recognizer;
    private SpeechSynthesizer? _synth;
    private bool _sttReady;
    private bool _ttsReady;
    private TaskCompletionSource<string?>? _listenTcs;

    // HUD Colors
    private static readonly Color CyanColor = (Color)ColorConverter.ConvertFromString("#FF00D4FF");
    private static readonly Color ArcBlue = (Color)ColorConverter.ConvertFromString("#FF1A8FFF");
    private static readonly Color DarkBg = (Color)ColorConverter.ConvertFromString("#FF050510");
    private static readonly Brush CyanBrush = new SolidColorBrush(CyanColor);
    private static readonly Brush CyanDimBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FF0099CC"));
    private static readonly Brush HudTextBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FFEAF6FF"));
    private static readonly Brush HudDimBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FF2A4A60"));
    private static readonly Brush HudMidBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FF5A8CAA"));
    private static readonly Brush UserBubbleBg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FF0A1228"));
    private static readonly Brush JarvisBubbleBg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FF081420"));
    private static readonly Brush JarvisBorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FF0D3B5E"));
    private static readonly Brush UserBorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FF1A2040"));
    private static readonly Brush RedBrush = new SolidColorBrush(Colors.Red);
    private static readonly Brush GreenBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FF34D399"));

    public MainWindow()
    {
        InitializeComponent();
        _deviceId = Environment.GetEnvironmentVariable("JARVIS_DEVICE_ID") ?? "windows-native";
        _brainWs = Environment.GetEnvironmentVariable("JARVIS_BRAIN_WS") ?? "ws://localhost:8400/ws";
        InputBindings.Add(new KeyBinding(new RelayCommand(_ => MicBtn_Click(null, null)), Key.Space, ModifierKeys.Control));
    }

    private async void Window_Loaded(object sender, RoutedEventArgs e)
    {
        InitVoice();
        await ConnectLoop();
    }

    // ══════════════════════════════════
    //  Voice
    // ══════════════════════════════════

    private void InitVoice()
    {
        try
        {
            _synth = new SpeechSynthesizer();
            _synth.SetOutputToDefaultAudioDevice();
            _synth.Rate = 1;
            foreach (var v in _synth.GetInstalledVoices())
                if (v.VoiceInfo.Name.Contains("David", StringComparison.OrdinalIgnoreCase) ||
                    v.VoiceInfo.Name.Contains("Mark", StringComparison.OrdinalIgnoreCase))
                { _synth.SelectVoice(v.VoiceInfo.Name); break; }
            _ttsReady = true;
        }
        catch { _ttsReady = false; }

        try
        {
            _recognizer = new SpeechRecognitionEngine(new CultureInfo("en-US"));
            _recognizer.LoadGrammar(new DictationGrammar());
            _recognizer.SetInputToDefaultAudioDevice();
            _recognizer.SpeechRecognized += (s, a) => _listenTcs?.TrySetResult(a.Result.Text);
            _recognizer.RecognizeCompleted += (s, a) => _listenTcs?.TrySetResult(null);
            _sttReady = true;
        }
        catch { _sttReady = false; }

        Dispatcher.Invoke(() =>
        {
            VoiceBadge.Text = _sttReady ? "VOICE: ON" : "VOICE: OFF";
            VoiceBadge.Foreground = _sttReady ? CyanBrush : RedBrush;
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
            if (result != _listenTcs.Task) { _recognizer.RecognizeAsyncCancel(); return null; }
            return await _listenTcs.Task;
        }
        catch { return null; }
    }

    private void Speak(string text)
    {
        if (!_ttsReady || _synth == null) return;
        Task.Run(() => { try { _synth.Speak(text); } catch { } });
    }

    // ══════════════════════════════════
    //  WebSocket
    // ══════════════════════════════════

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

                await WsSend(JsonSerializer.Serialize(new
                {
                    @event = "agent_connect", device_id = _deviceId, platform = "windows",
                    capabilities = new[] { "os_control", "apps", "files", "browser", "terminal", "clipboard", "system", "voice" }
                }));

                var ack = await WsReceive();
                if (ack?.RootElement.GetProperty("event").GetString() == "connected")
                {
                    _connected = true; delay = 1000;
                    Dispatcher.Invoke(() =>
                    {
                        StatusDotFill.Color = (Color)ColorConverter.ConvertFromString("#FF34D399");
                        StatusText.Text = "ONLINE";
                        StatusText.Foreground = GreenBrush;
                        AddSystemMessage("// BRAIN LINK ESTABLISHED");
                    });
                }

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
                StatusDotFill.Color = (Color)ColorConverter.ConvertFromString("#FFF87171");
                StatusText.Text = "OFFLINE";
                StatusText.Foreground = RedBrush;
            });
            await Task.Delay(delay, CancellationToken.None);
            delay = Math.Min(delay * 2, 30000);
        }
    }

    private async Task WsSend(string text)
    {
        if (_ws?.State != WebSocketState.Open) return;
        await _ws.SendAsync(Encoding.UTF8.GetBytes(text), WebSocketMessageType.Text, true, _cts.Token);
    }

    private async Task<JsonDocument?> WsReceive()
    {
        var buf = new byte[65536];
        var sb = new StringBuilder();
        WebSocketReceiveResult result;
        do { result = await _ws!.ReceiveAsync(buf, _cts.Token); sb.Append(Encoding.UTF8.GetString(buf, 0, result.Count)); }
        while (!result.EndOfMessage);
        return result.MessageType == WebSocketMessageType.Close ? null : JsonDocument.Parse(sb.ToString());
    }

    private void HandleMessage(JsonDocument doc)
    {
        var ev = doc.RootElement.GetProperty("event").GetString();
        if (ev == "response")
        {
            if (doc.RootElement.TryGetProperty("text", out var tp))
            {
                var text = tp.GetString() ?? "";
                if (!string.IsNullOrWhiteSpace(text))
                {
                    Dispatcher.Invoke(() => AddMessage("jarvis", text));
                    if (doc.RootElement.TryGetProperty("tts", out var tts) && tts.GetBoolean()) Speak(text);
                }
            }
            if (doc.RootElement.TryGetProperty("actions", out var ap))
                foreach (var a in ap.EnumerateArray()) ExecuteAction(a);
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
        await WsSend(JsonSerializer.Serialize(new { @event = "user_input", device_id = _deviceId, text }));
    }

    private void ExecuteAction(JsonElement act)
    {
        var type = act.GetProperty("type").GetString() ?? "";
        var target = act.TryGetProperty("target", out var tp) ? tp.GetString() ?? "" : "";
        Task.Run(() =>
        {
            try
            {
                if (type == "open_app") Process.Start(new ProcessStartInfo { FileName = target, UseShellExecute = true });
                else if (type == "open_url") Process.Start(new ProcessStartInfo { FileName = target.StartsWith("http") ? target : $"https://{target}", UseShellExecute = true });
                else if (type == "search") Process.Start(new ProcessStartInfo { FileName = $"https://www.google.com/search?q={Uri.EscapeDataString(target)}", UseShellExecute = true });
                Dispatcher.Invoke(() => AddSystemMessage($"// EXECUTED: {type} {target}"));
            }
            catch (Exception ex) { Dispatcher.Invoke(() => AddSystemMessage($"// ERROR: {ex.Message}")); }
        });
    }

    // ══════════════════════════════════
    //  UI Events
    // ══════════════════════════════════

    private async void SendBtn_Click(object? sender, RoutedEventArgs? e)
    {
        var text = InputBox.Text.Trim();
        if (string.IsNullOrEmpty(text)) return;
        InputBox.Text = "";
        AddMessage("user", text);
        ShowTyping(true);
        await SendToBrain(text);
    }

    private void InputBox_KeyDown(object sender, KeyEventArgs e) { if (e.Key == Key.Enter) SendBtn_Click(null, null); }

    private async void MicBtn_Click(object? sender, RoutedEventArgs? e)
    {
        if (_listening || !_sttReady) return;
        _listening = true;
        MicBtn.Content = "🔴";
        AddSystemMessage("// LISTENING...");

        var text = await Task.Run(ListenAsync);

        _listening = false;
        Dispatcher.Invoke(() => MicBtn.Content = "🎤");

        if (!string.IsNullOrWhiteSpace(text))
        { AddMessage("user", text); ShowTyping(true); await SendToBrain(text); }
        else
        { AddSystemMessage("// NO INPUT DETECTED"); }
    }

    private void Window_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        _cts.Cancel(); _synth?.Dispose(); _recognizer?.Dispose(); _ws?.Dispose();
    }

    // ══════════════════════════════════
    //  Chat Rendering -- Iron Man HUD
    // ══════════════════════════════════

    private void AddMessage(string role, string text)
    {
        ShowTyping(false);
        bool isUser = role == "user";
        var time = DateTime.Now.ToString("HH:mm:ss");

        var container = new Border
        {
            Margin = new Thickness(0, 6, 0, 6),
            HorizontalAlignment = isUser ? HorizontalAlignment.Right : HorizontalAlignment.Left,
            MaxWidth = 400,
        };

        var row = new StackPanel { Orientation = Orientation.Horizontal };

        // Avatar -- arc reactor style for Jarvis
        var avatarGrid = new Grid
        {
            Width = 34, Height = 34,
            Margin = isUser ? new Thickness(10, 0, 0, 0) : new Thickness(0, 0, 10, 0),
            VerticalAlignment = VerticalAlignment.Top,
        };

        if (!isUser)
        {
            // Jarvis: mini arc reactor
            avatarGrid.Children.Add(new Ellipse
            {
                Width = 34, Height = 34, StrokeThickness = 1.5,
                Stroke = CyanDimBrush, Opacity = 0.6,
            });
            avatarGrid.Children.Add(new Ellipse
            {
                Width = 20, Height = 20,
                Fill = new RadialGradientBrush(CyanColor, ArcBlue) { GradientOrigin = new Point(0.3, 0.3) },
                Effect = new DropShadowEffect { Color = CyanColor, BlurRadius = 10, ShadowDepth = 0, Opacity = 0.5 },
            });
            avatarGrid.Children.Add(new TextBlock
            {
                Text = "J", Foreground = Brushes.White, FontSize = 9, FontWeight = FontWeights.Bold,
                HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center,
            });
        }
        else
        {
            avatarGrid.Children.Add(new Ellipse
            {
                Width = 34, Height = 34, StrokeThickness = 1,
                Stroke = UserBorderBrush,
                Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FF0A0A20")),
            });
            avatarGrid.Children.Add(new TextBlock
            {
                Text = "U", Foreground = HudMidBrush, FontSize = 13, FontWeight = FontWeights.SemiBold,
                HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center,
            });
        }

        // Bubble
        var bubble = new Border
        {
            CornerRadius = new CornerRadius(isUser ? 14 : 2, isUser ? 2 : 14, 14, 14),
            Padding = new Thickness(14, 10, 14, 10),
            Background = isUser ? UserBubbleBg : JarvisBubbleBg,
            BorderBrush = isUser ? UserBorderBrush : JarvisBorderBrush,
            BorderThickness = new Thickness(1),
        };

        if (!isUser)
        {
            bubble.Effect = new DropShadowEffect
            {
                Color = CyanColor, BlurRadius = 8, ShadowDepth = 0, Opacity = 0.08,
            };
        }

        var inner = new StackPanel();

        // Header with HUD label
        var header = new DockPanel { Margin = new Thickness(0, 0, 0, 4) };
        var nameBlock = new TextBlock
        {
            Text = isUser ? "USER" : "J.A.R.V.I.S.",
            FontSize = 10, FontWeight = FontWeights.SemiBold,
            FontFamily = new FontFamily("Consolas"),
            Foreground = isUser ? HudMidBrush : CyanBrush,
        };
        var timeBlock = new TextBlock
        {
            Text = time, FontSize = 9, FontFamily = new FontFamily("Consolas"),
            Foreground = HudDimBrush, Margin = new Thickness(12, 0, 0, 0),
        };
        DockPanel.SetDock(timeBlock, Dock.Right);
        header.Children.Add(timeBlock);
        header.Children.Add(nameBlock);
        inner.Children.Add(header);

        // Separator line
        inner.Children.Add(new Rectangle
        {
            Height = 1, Margin = new Thickness(0, 3, 0, 6), Opacity = 0.15,
            Fill = isUser ? UserBorderBrush : CyanDimBrush,
        });

        // Text
        inner.Children.Add(new TextBlock
        {
            Text = text, FontSize = 13, LineHeight = 21,
            Foreground = HudTextBrush, TextWrapping = TextWrapping.Wrap,
            FontFamily = new FontFamily("Segoe UI"),
        });

        bubble.Child = inner;

        if (isUser) { row.Children.Add(bubble); row.Children.Add(avatarGrid); }
        else { row.Children.Add(avatarGrid); row.Children.Add(bubble); }

        container.Child = row;

        // Slide + fade animation
        container.Opacity = 0;
        container.RenderTransform = new TranslateTransform(0, 12);
        ChatPanel.Children.Add(container);

        var fadeIn = new DoubleAnimation(0, 1, TimeSpan.FromMilliseconds(250));
        var slideUp = new DoubleAnimation(12, 0, TimeSpan.FromMilliseconds(250))
        {
            EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut }
        };
        container.BeginAnimation(OpacityProperty, fadeIn);
        ((TranslateTransform)container.RenderTransform).BeginAnimation(TranslateTransform.YProperty, slideUp);

        ScrollToBottom();
    }

    private void AddSystemMessage(string text)
    {
        ShowTyping(false);
        var tb = new TextBlock
        {
            Text = text, FontSize = 10,
            FontFamily = new FontFamily("Consolas"),
            Foreground = HudDimBrush,
            HorizontalAlignment = HorizontalAlignment.Center,
            Margin = new Thickness(0, 6, 0, 4),
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
                Text = "// PROCESSING...",
                FontSize = 10, FontFamily = new FontFamily("Consolas"),
                FontStyle = FontStyles.Normal,
                Foreground = CyanDimBrush,
                Margin = new Thickness(44, 6, 0, 6),
                Opacity = 0.7,
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

public class RelayCommand : ICommand
{
    private readonly Action<object?> _execute;
    public RelayCommand(Action<object?> execute) => _execute = execute;
    public event EventHandler? CanExecuteChanged;
    public bool CanExecute(object? parameter) => true;
    public void Execute(object? parameter) => _execute(parameter);
}
