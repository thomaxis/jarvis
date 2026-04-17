using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net.WebSockets;
using System.Speech.Recognition;
using System.Speech.Synthesis;
using System.Text;
using System.Text.Json;
using System.Windows;
using Microsoft.Web.WebView2.Core;

namespace JarvisApp;

public partial class MainWindow : Window
{
    private ClientWebSocket? _ws;
    private bool _connected;
    private bool _listening;
    private string _deviceId;
    private string _brainWs;
    private readonly CancellationTokenSource _cts = new();

    private SpeechRecognitionEngine? _recognizer;
    private SpeechSynthesizer? _synth;
    private bool _sttReady, _ttsReady, _sttEnabled = true, _ttsEnabled = true;
    private TaskCompletionSource<string?>? _listenTcs;

    public MainWindow()
    {
        InitializeComponent();
        _deviceId = Environment.GetEnvironmentVariable("JARVIS_DEVICE_ID") ?? "jarvis-windows";
        _brainWs = Environment.GetEnvironmentVariable("JARVIS_BRAIN_WS") ?? "ws://localhost:8400/ws";
    }

    private async void Window_Loaded(object sender, RoutedEventArgs e)
    {
        InitVoice();
        await InitWebView();
        _ = ConnectLoop();
    }

    // ═══ WebView ═══

    private async Task InitWebView()
    {
        var env = await CoreWebView2Environment.CreateAsync(null, Path.GetTempPath());
        await WebView.EnsureCoreWebView2Async(env);
        WebView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
        WebView.CoreWebView2.Settings.IsStatusBarEnabled = false;
        WebView.CoreWebView2.Settings.AreDevToolsEnabled = false;
        WebView.CoreWebView2.WebMessageReceived += OnWebMessage;
        WebView.CoreWebView2.NavigateToString(BuildHtml());
    }

    private void CallJs(string fn, params object[] args)
    {
        var argsStr = string.Join(",", args.Select(a => JsonSerializer.Serialize(a)));
        Dispatcher.InvokeAsync(() =>
        {
            try { WebView.CoreWebView2?.ExecuteScriptAsync($"window.J.{fn}({argsStr})"); } catch { }
        });
    }

    private async void OnWebMessage(object? s, CoreWebView2WebMessageReceivedEventArgs e)
    {
        var raw = e.WebMessageAsJson;
        var doc = JsonDocument.Parse(raw);
        var action = doc.RootElement.GetProperty("action").GetString();

        switch (action)
        {
            case "send":
                var text = doc.RootElement.GetProperty("text").GetString() ?? "";
                if (!string.IsNullOrWhiteSpace(text))
                {
                    CallJs("addMsg", "user", text);
                    CallJs("showTyping", true);
                    await SendToBrain(text);
                }
                break;
            case "mic":
                _ = DoListen();
                break;
            case "setStt":
                _sttEnabled = doc.RootElement.GetProperty("value").GetBoolean();
                break;
            case "setTts":
                _ttsEnabled = doc.RootElement.GetProperty("value").GetBoolean();
                break;
            case "setSpeed":
                if (_synth != null)
                    _synth.Rate = doc.RootElement.GetProperty("value").GetInt32();
                break;
            case "setBrainUrl":
                _brainWs = doc.RootElement.GetProperty("value").GetString() ?? _brainWs;
                break;
            case "setDeviceId":
                _deviceId = doc.RootElement.GetProperty("value").GetString() ?? _deviceId;
                break;
        }
    }

    // ═══ Voice ═══

    private void InitVoice()
    {
        try
        {
            _synth = new SpeechSynthesizer();
            _synth.SetOutputToDefaultAudioDevice();
            _synth.Rate = 1;
            foreach (var v in _synth.GetInstalledVoices())
                if (v.VoiceInfo.Name.Contains("David", StringComparison.OrdinalIgnoreCase) ||
                    v.VoiceInfo.Name.Contains("Mark", StringComparison.OrdinalIgnoreCase) ||
                    v.VoiceInfo.Name.Contains("Zira", StringComparison.OrdinalIgnoreCase))
                { _synth.SelectVoice(v.VoiceInfo.Name); break; }
            _ttsReady = true;
        }
        catch { }

        try
        {
            _recognizer = new SpeechRecognitionEngine(new CultureInfo("en-US"));
            _recognizer.LoadGrammar(new DictationGrammar());
            _recognizer.SetInputToDefaultAudioDevice();
            _recognizer.SpeechRecognized += (_, a) => _listenTcs?.TrySetResult(a.Result.Text);
            _recognizer.RecognizeCompleted += (_, _) => _listenTcs?.TrySetResult(null);
            _sttReady = true;
        }
        catch { }
    }

    private async Task DoListen()
    {
        if (_listening || !_sttReady || !_sttEnabled) return;
        _listening = true;
        CallJs("setListening", true);

        string? text = null;
        try
        {
            _listenTcs = new TaskCompletionSource<string?>();
            _recognizer!.RecognizeAsync(RecognizeMode.Single);
            var done = await Task.WhenAny(_listenTcs.Task, Task.Delay(10000));
            if (done == _listenTcs.Task) text = await _listenTcs.Task;
            else _recognizer.RecognizeAsyncCancel();
        }
        catch { }

        _listening = false;
        CallJs("setListening", false);

        if (!string.IsNullOrWhiteSpace(text))
        {
            CallJs("addMsg", "user", text);
            CallJs("showTyping", true);
            await SendToBrain(text);
        }
        else
        {
            CallJs("addSys", "No voice detected. Try again.");
        }
    }

    private void Speak(string text)
    {
        if (!_ttsReady || !_ttsEnabled || _synth == null) return;
        Task.Run(() => { try { _synth.Speak(text); } catch { } });
    }

    // ═══ WebSocket ═══

    private async Task ConnectLoop()
    {
        int delay = 1000;
        while (!_cts.IsCancellationRequested)
        {
            try
            {
                _ws = new ClientWebSocket();
                var tok = Environment.GetEnvironmentVariable("JARVIS_AGENT_TOKEN");
                if (!string.IsNullOrEmpty(tok)) _ws.Options.SetRequestHeader("Authorization", $"Bearer {tok}");
                await _ws.ConnectAsync(new Uri(_brainWs), _cts.Token);

                await WsSend(JsonSerializer.Serialize(new {
                    @event = "agent_connect", device_id = _deviceId, platform = "windows",
                    capabilities = new[] { "os_control","apps","files","browser","terminal","clipboard","system","voice" }
                }));
                var ack = await WsRecv();
                if (ack?.RootElement.GetProperty("event").GetString() == "connected")
                {
                    _connected = true; delay = 1000;
                    CallJs("setConnected", true);
                }
                while (_ws.State == WebSocketState.Open && !_cts.IsCancellationRequested)
                {
                    var msg = await WsRecv();
                    if (msg != null) HandleMsg(msg);
                }
            }
            catch { }
            _connected = false;
            CallJs("setConnected", false);
            await Task.Delay(delay, CancellationToken.None);
            delay = Math.Min(delay * 2, 30000);
        }
    }

    private async Task WsSend(string t)
    {
        if (_ws?.State == WebSocketState.Open)
            await _ws.SendAsync(Encoding.UTF8.GetBytes(t), WebSocketMessageType.Text, true, _cts.Token);
    }

    private async Task<JsonDocument?> WsRecv()
    {
        var buf = new byte[65536]; var sb = new StringBuilder();
        WebSocketReceiveResult r;
        do { r = await _ws!.ReceiveAsync(buf, _cts.Token); sb.Append(Encoding.UTF8.GetString(buf, 0, r.Count)); } while (!r.EndOfMessage);
        return r.MessageType == WebSocketMessageType.Close ? null : JsonDocument.Parse(sb.ToString());
    }

    private async Task SendToBrain(string text)
    {
        if (!_connected) { CallJs("addSys", "Not connected."); return; }
        await WsSend(JsonSerializer.Serialize(new { @event = "user_input", device_id = _deviceId, text }));
    }

    private void HandleMsg(JsonDocument doc)
    {
        var ev = doc.RootElement.GetProperty("event").GetString();
        if (ev == "response")
        {
            if (doc.RootElement.TryGetProperty("text", out var tp))
            {
                var t = tp.GetString() ?? "";
                if (t.Length > 0) { CallJs("addMsg", "jarvis", t); Speak(t); }
            }
            if (doc.RootElement.TryGetProperty("actions", out var ap))
                foreach (var a in ap.EnumerateArray()) ExecAction(a);
        }
        else if (ev == "notification")
            CallJs("addSys", doc.RootElement.TryGetProperty("message", out var m) ? m.GetString() ?? "" : "");
    }

    private void ExecAction(JsonElement a)
    {
        var type = a.GetProperty("type").GetString() ?? "";
        var tgt = a.TryGetProperty("target", out var t) ? t.GetString() ?? "" : "";
        Task.Run(() => {
            try {
                if (type is "open_app") Process.Start(new ProcessStartInfo { FileName = tgt, UseShellExecute = true });
                else if (type is "open_url") Process.Start(new ProcessStartInfo { FileName = tgt.StartsWith("http") ? tgt : $"https://{tgt}", UseShellExecute = true });
                else if (type is "search") Process.Start(new ProcessStartInfo { FileName = $"https://www.google.com/search?q={Uri.EscapeDataString(tgt)}", UseShellExecute = true });
                CallJs("addSys", $"Executed: {type} {tgt}");
            } catch (Exception ex) { CallJs("addSys", $"Error: {ex.Message}"); }
        });
    }

    private void Window_Closing(object? s, System.ComponentModel.CancelEventArgs e)
    { _cts.Cancel(); _synth?.Dispose(); _recognizer?.Dispose(); _ws?.Dispose(); }

    // ═══ HTML UI ═══

    private string BuildHtml() => $@"<!DOCTYPE html>
<html><head><meta charset=""UTF-8"">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#030308;--bg2:#080812;--bg3:#0c0c1a;
  --surface:#0e1025;--surface2:#121230;
  --cyan:#00d4ff;--cyan2:#0099cc;--cyan3:#006699;--cyanglow:#00d4ff40;
  --arc:#1a8fff;--blue:#0055ff;
  --red:#ff4466;--green:#00ffaa;--amber:#ffaa00;
  --text:#e8f0ff;--text2:#8899bb;--text3:#3a4a66;
  --border:#0d2040;--border2:#1a3060;
}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);
  height:100vh;display:flex;flex-direction:column;overflow:hidden;-webkit-font-smoothing:antialiased}}

/* ── HEADER ── */
.hdr{{display:flex;align-items:center;padding:16px 22px;background:var(--bg2);position:relative;flex-shrink:0}}
.hdr::after{{content:'';position:absolute;bottom:0;left:10%;right:10%;height:1px;
  background:linear-gradient(90deg,transparent,var(--cyan3),var(--cyan),var(--cyan3),transparent);opacity:.4}}

.arc{{width:52px;height:52px;position:relative;margin-right:16px;flex-shrink:0}}
.arc .ring{{position:absolute;inset:0;border:2px solid var(--cyan2);border-radius:50%;opacity:.5;
  border-top-color:transparent;border-left-color:transparent;animation:spin 6s linear infinite}}
.arc .ring2{{position:absolute;inset:4px;border:1.5px dashed var(--cyan3);border-radius:50%;opacity:.3;
  animation:spin 10s linear infinite reverse}}
.arc .core{{position:absolute;inset:10px;border-radius:50%;
  background:radial-gradient(circle,var(--cyan),var(--arc) 50%,#051020 100%);
  box-shadow:0 0 25px var(--cyanglow),0 0 50px #00d4ff20,inset 0 0 10px #00d4ff30}}
.arc .core span{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-family:'JetBrains Mono';font-weight:700;font-size:14px;color:white;text-shadow:0 0 8px var(--cyan)}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}

.title{{flex:1}}
.title h1{{font-family:'JetBrains Mono';font-size:19px;font-weight:700;color:var(--cyan);
  letter-spacing:3px;text-shadow:0 0 12px var(--cyanglow)}}
.title .status{{display:flex;align-items:center;gap:6px;margin-top:4px}}
.title .dot{{width:6px;height:6px;border-radius:50%;background:var(--red);transition:.3s;flex-shrink:0}}
.title .dot.on{{background:var(--green);box-shadow:0 0 8px var(--green)}}
.title .status span{{font-family:'JetBrains Mono';font-size:10px;color:var(--text3);letter-spacing:1px}}

.hdr-btns{{display:flex;gap:8px}}
.hdr-btn{{width:36px;height:36px;border-radius:8px;border:1px solid var(--border);background:var(--surface);
  color:var(--text2);display:flex;align-items:center;justify-content:center;cursor:pointer;
  font-size:15px;transition:.2s}}
.hdr-btn:hover{{border-color:var(--cyan2);color:var(--cyan);background:var(--surface2)}}

/* ── CHAT ── */
.chat{{flex:1;overflow-y:auto;padding:16px 20px;display:flex;flex-direction:column;gap:8px}}
.chat::-webkit-scrollbar{{width:5px}}.chat::-webkit-scrollbar-track{{background:transparent}}
.chat::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}

.msg{{display:flex;gap:10px;max-width:90%;animation:msgIn .3s ease-out}}
.msg.user{{align-self:flex-end;flex-direction:row-reverse}}
.msg.jarvis{{align-self:flex-start}}
@keyframes msgIn{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}

.msg .av{{width:30px;height:30px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;
  justify-content:center;font-family:'JetBrains Mono';font-size:11px;font-weight:700;margin-top:2px}}
.msg.jarvis .av{{background:radial-gradient(circle,var(--cyan),var(--arc));color:white;
  box-shadow:0 0 12px var(--cyanglow)}}
.msg.user .av{{background:var(--surface2);border:1px solid var(--border);color:var(--text2)}}

.msg .bub{{padding:10px 14px;border-radius:14px;font-size:13px;line-height:1.6;position:relative}}
.msg.jarvis .bub{{background:linear-gradient(135deg,#0a1428,#081020);border:1px solid var(--border2);
  border-bottom-left-radius:4px;box-shadow:0 0 12px #00d4ff08}}
.msg.user .bub{{background:var(--surface);border:1px solid var(--border);border-bottom-right-radius:4px}}
.bub .nm{{font-family:'JetBrains Mono';font-size:10px;font-weight:600;margin-bottom:4px;
  display:flex;justify-content:space-between;gap:16px}}
.msg.jarvis .nm .n{{color:var(--cyan)}}.msg.user .nm .n{{color:var(--text2)}}
.nm .t{{color:var(--text3);font-weight:400}}
.bub .ln{{height:1px;background:var(--border);margin:4px 0 6px;opacity:.4}}

.sys{{text-align:center;font-family:'JetBrains Mono';font-size:10px;color:var(--text3);
  padding:6px 0;letter-spacing:.5px;animation:msgIn .2s ease-out}}

.typing{{display:none;align-self:flex-start;padding:4px 0;animation:msgIn .2s}}
.typing.show{{display:flex}}.typing-inner{{display:flex;gap:4px;padding:10px 16px;
  background:linear-gradient(135deg,#0a1428,#081020);border-radius:14px;border:1px solid var(--border2)}}
.typing-inner span{{width:5px;height:5px;border-radius:50%;background:var(--cyan2);animation:dot 1.2s infinite}}
.typing-inner span:nth-child(2){{animation-delay:.15s}}.typing-inner span:nth-child(3){{animation-delay:.3s}}
@keyframes dot{{0%,60%,100%{{transform:translateY(0);opacity:.4}}30%{{transform:translateY(-6px);opacity:1}}}}

/* ── INPUT ── */
.input-area{{padding:14px 20px 18px;background:var(--bg2);flex-shrink:0;
  border-top:1px solid var(--border)}}
.input-row{{display:flex;align-items:center;gap:8px;background:var(--bg3);
  border:1px solid var(--border);border-radius:26px;padding:5px 5px 5px 6px;transition:.3s}}
.input-row:focus-within{{border-color:var(--cyan2);box-shadow:0 0 0 3px var(--cyanglow)}}

.mic{{width:42px;height:42px;border-radius:50%;border:1.5px solid var(--border2);background:var(--surface);
  color:var(--cyan);display:flex;align-items:center;justify-content:center;cursor:pointer;
  transition:.2s;flex-shrink:0;font-size:16px}}
.mic:hover{{border-color:var(--cyan);background:var(--surface2)}}
.mic.rec{{border-color:var(--red);background:#1a0010;color:var(--red);
  animation:pulse 1.5s infinite;box-shadow:0 0 15px #ff446640}}
@keyframes pulse{{0%,100%{{box-shadow:0 0 0 0 #ff446640}}50%{{box-shadow:0 0 0 10px #ff446600}}}}

.inp{{flex:1;border:none;outline:none;background:transparent;color:var(--text);
  font-family:'Inter';font-size:14px;padding:8px 6px}}
.inp::placeholder{{color:var(--text3)}}

.send{{width:42px;height:42px;border-radius:50%;border:none;cursor:pointer;
  display:flex;align-items:center;justify-content:center;font-size:15px;color:white;transition:.15s;flex-shrink:0;
  background:linear-gradient(135deg,var(--cyan),var(--arc));
  box-shadow:0 0 16px var(--cyanglow)}}
.send:hover{{opacity:.85;transform:scale(1.05)}}.send:active{{transform:scale(.95)}}

/* ── SETTINGS ── */
.settings{{position:absolute;inset:0;background:#030308ee;z-index:100;display:none;
  justify-content:center;align-items:center;animation:fadeIn .2s}}
.settings.show{{display:flex}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
.spanel{{width:88%;max-width:420px;background:var(--bg2);border:1px solid var(--border2);
  border-radius:16px;padding:28px;box-shadow:0 0 40px #00d4ff08;max-height:80vh;overflow-y:auto}}
.spanel h2{{font-family:'JetBrains Mono';font-size:14px;color:var(--cyan);letter-spacing:2px;
  margin-bottom:20px;display:flex;justify-content:space-between;align-items:center}}
.spanel h2 .x{{cursor:pointer;color:var(--text3);font-size:18px;transition:.2s}}
.spanel h2 .x:hover{{color:var(--cyan)}}
.sdiv{{height:1px;background:linear-gradient(90deg,transparent,var(--cyan3),transparent);
  margin:16px 0;opacity:.3}}
.srow{{display:flex;justify-content:space-between;align-items:center;padding:10px 0}}
.srow .slbl{{font-size:12px;color:var(--text)}}
.srow .sdesc{{font-size:10px;color:var(--text3);margin-top:2px}}
/* toggle */
.tog{{width:44px;height:24px;border-radius:12px;background:var(--surface);border:1px solid var(--border);
  cursor:pointer;position:relative;transition:.3s;flex-shrink:0}}
.tog.on{{background:var(--cyan3);border-color:var(--cyan2)}}
.tog::after{{content:'';width:18px;height:18px;border-radius:50%;background:var(--text2);
  position:absolute;top:2px;left:2px;transition:.3s}}
.tog.on::after{{transform:translateX(20px);background:var(--cyan)}}
/* range */
.srange{{width:100%;margin:8px 0;accent-color:var(--cyan)}}
.sinput{{width:100%;padding:8px 12px;background:var(--surface);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-family:'JetBrains Mono';font-size:12px;outline:none;
  transition:.2s}}
.sinput:focus{{border-color:var(--cyan2);box-shadow:0 0 0 2px var(--cyanglow)}}
.sinfo{{font-family:'JetBrains Mono';font-size:10px;color:var(--text3);margin-top:16px;text-align:center}}
</style></head>
<body>
<div class=""hdr"">
  <div class=""arc""><div class=""ring""></div><div class=""ring2""></div><div class=""core""><span>J</span></div></div>
  <div class=""title"">
    <h1>J.A.R.V.I.S.</h1>
    <div class=""status""><div class=""dot"" id=""dot""></div><span id=""stxt"">INITIALIZING</span></div>
  </div>
  <div class=""hdr-btns"">
    <div class=""hdr-btn"" id=""settingsBtn"" title=""Settings"">&#9881;</div>
  </div>
</div>

<div class=""chat"" id=""chat"">
  <div class=""sys"">S Y S T E M &nbsp; O N L I N E</div>
</div>
<div class=""typing"" id=""typing""><div style=""width:40px""></div><div class=""typing-inner""><span></span><span></span><span></span></div></div>

<div class=""input-area"">
  <div class=""input-row"">
    <div class=""mic"" id=""mic"" onclick=""J.mic()"" title=""Push to talk (Ctrl+Space)"">&#127908;</div>
    <input class=""inp"" id=""inp"" placeholder=""Talk to Jarvis..."" autocomplete=""off""/>
    <button class=""send"" onclick=""J.send()"">&#10148;</button>
  </div>
</div>

<div class=""settings"" id=""settings"">
  <div class=""spanel"">
    <h2>&#9881; &nbsp;S E T T I N G S<span class=""x"" onclick=""J.toggleSettings()"">&#10005;</span></h2>
    <div class=""sdiv""></div>
    <div class=""srow""><div><div class=""slbl"">Voice Input (STT)</div><div class=""sdesc"">Microphone speech recognition</div></div>
      <div class=""tog on"" id=""tstt"" onclick=""J.togStt(this)""></div></div>
    <div class=""srow""><div><div class=""slbl"">Voice Output (TTS)</div><div class=""sdesc"">Jarvis speaks responses</div></div>
      <div class=""tog on"" id=""ttts"" onclick=""J.togTts(this)""></div></div>
    <div class=""srow"" style=""flex-direction:column;align-items:stretch"">
      <div style=""display:flex;justify-content:space-between""><span class=""slbl"">Voice Speed</span><span class=""slbl"" id=""speedLbl"" style=""color:var(--cyan)"">1</span></div>
      <input type=""range"" class=""srange"" min=""-5"" max=""5"" value=""1"" id=""speed"" oninput=""J.setSpeed(this.value)""/>
    </div>
    <div class=""sdiv""></div>
    <div class=""srow"" style=""flex-direction:column;align-items:stretch"">
      <div class=""slbl"" style=""margin-bottom:6px"">Brain URL</div>
      <input class=""sinput"" id=""brainUrl"" value=""{_brainWs}"" onchange=""J.setBrain(this.value)""/>
    </div>
    <div class=""srow"" style=""flex-direction:column;align-items:stretch;margin-top:8px"">
      <div class=""slbl"" style=""margin-bottom:6px"">Device ID</div>
      <input class=""sinput"" id=""devId"" value=""{_deviceId}"" onchange=""J.setDev(this.value)""/>
    </div>
    <div class=""sdiv""></div>
    <div class=""sinfo"">J.A.R.V.I.S. v0.1.0 &bull; .NET 9 &bull; WebView2 &bull; Windows Speech</div>
  </div>
</div>

<script>
const $=id=>document.getElementById(id);const chat=$('chat');const inp=$('inp');const mic=$('mic');
const typing=$('typing');const dot=$('dot');const stxt=$('stxt');

window.J={{
  addMsg(role,text){{
    this.showTyping(false);
    const u=role==='user';const t=new Date().toLocaleTimeString([],{{hour:'2-digit',minute:'2-digit',second:'2-digit'}});
    const d=document.createElement('div');d.className='msg '+(u?'user':'jarvis');
    d.innerHTML=`<div class=""av"">${{u?'U':'J'}}</div><div class=""bub""><div class=""nm""><span class=""n"">${{u?'USER':'J.A.R.V.I.S.'}}</span><span class=""t"">${{t}}</span></div><div class=""ln""></div>${{this.esc(text)}}</div>`;
    chat.appendChild(d);this.scroll();
  }},
  addSys(text){{
    this.showTyping(false);
    const d=document.createElement('div');d.className='sys';d.textContent=text;
    chat.appendChild(d);this.scroll();
  }},
  showTyping(s){{typing.classList.toggle('show',s);if(s)this.scroll()}},
  setConnected(on){{dot.classList.toggle('on',on);stxt.textContent=on?'ONLINE':'OFFLINE';
    if(on)this.addSys('Brain link established')}},
  setListening(on){{mic.classList.toggle('rec',on);if(on)this.addSys('Listening... speak now')}},
  send(){{const t=inp.value.trim();if(!t)return;inp.value='';
    window.chrome.webview.postMessage({{action:'send',text:t}})}},
  mic(){{window.chrome.webview.postMessage({{action:'mic'}})}},
  toggleSettings(){{$('settings').classList.toggle('show')}},
  togStt(el){{el.classList.toggle('on');window.chrome.webview.postMessage({{action:'setStt',value:el.classList.contains('on')}});
    mic.style.display=el.classList.contains('on')?'flex':'none'}},
  togTts(el){{el.classList.toggle('on');window.chrome.webview.postMessage({{action:'setTts',value:el.classList.contains('on')}})}},
  setSpeed(v){{$('speedLbl').textContent=v;window.chrome.webview.postMessage({{action:'setSpeed',value:parseInt(v)}})}},
  setBrain(v){{window.chrome.webview.postMessage({{action:'setBrainUrl',value:v}})}},
  setDev(v){{window.chrome.webview.postMessage({{action:'setDeviceId',value:v}})}},
  scroll(){{setTimeout(()=>chat.scrollTop=chat.scrollHeight,30)}},
  esc(t){{const d=document.createElement('div');d.textContent=t;return d.innerHTML.replace(/\n/g,'<br>')}}
}};
inp.addEventListener('keydown',e=>{{if(e.key==='Enter')J.send()}});
document.addEventListener('keydown',e=>{{if(e.ctrlKey&&e.code==='Space'){{e.preventDefault();J.mic()}}}});
$('settingsBtn').addEventListener('click',()=>J.toggleSettings());
inp.focus();
</script>
</body></html>";
}

public class RelayCommand : System.Windows.Input.ICommand
{
    private readonly Action<object?> _exec;
    public RelayCommand(Action<object?> exec) => _exec = exec;
    public event EventHandler? CanExecuteChanged;
    public bool CanExecute(object? p) => true;
    public void Execute(object? p) => _exec(p);
}
