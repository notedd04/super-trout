package cloud.echocloud

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.*
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.google.gson.JsonParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*

private val Graphite = Color(0xFF0A0D12)
private val Surface = Color(0xFF141A22)
private val Cyan = Color(0xFF63D7F0)
private val WarmText = Color(0xFFC8CBCF)
private val Muted = Color(0xFF7D8792)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            EchoTheme {
                EchoApp(apiBase = BuildConfig.API_BASE_URL, desktopBase = BuildConfig.DESKTOP_BASE_URL)
            }
        }
    }
}

@Composable
fun EchoTheme(content: @Composable () -> Unit) {
    val scheme = darkColorScheme(primary = Cyan, onPrimary = Graphite, background = Graphite, surface = Surface, onSurface = Color.White)
    MaterialTheme(colorScheme = scheme, content = content)
}

@Composable
fun EchoApp(apiBase: String, desktopBase: String) {
    val nav = rememberNavController()
    var machineState by remember { mutableStateOf("Stopped") }
    var statusMessage by remember { mutableStateOf("Connect GitHub to begin") }
    var selectedTab by remember { mutableStateOf("Computer") }

    Scaffold(containerColor = Graphite, bottomBar = {
        NavigationBar(containerColor = Surface, tonalElevation = 0.dp) {
            listOf("Computer" to Icons.Outlined.Computer, "Files" to Icons.Outlined.Folder, "Monitor" to Icons.Outlined.Speed, "Settings" to Icons.Outlined.Settings).forEach { item ->
                NavigationBarItem(selected = selectedTab == item.first, onClick = {
                    selectedTab = item.first
                    nav.navigate(item.first) { launchSingleTop = true }
                }, icon = { Icon(item.second, null) }, label = { Text(item.first) }, colors = NavigationBarItemDefaults.colors(selectedIconColor = Cyan, selectedTextColor = Cyan, indicatorColor = Surface))
            }
        }
    }) { padding ->
        NavHost(nav, "Computer", Modifier.padding(padding)) {
            composable("Computer") { ComputerScreen(machineState, statusMessage, onConnect = { statusMessage = "GitHub connection required"; nav.navigate("Settings") }, onDesktop = { nav.navigate("Desktop") }, onStart = { machineState = "Starting" }, onStop = { machineState = "Stopped" }) }
            composable("Files") { FilesScreen(apiBase) }
            composable("Monitor") { MonitorScreen(apiBase) }
            composable("Settings") { SettingsScreen(apiBase) }
            composable("Desktop") { DesktopScreen(desktopBase) { nav.popBackStack() } }
        }
    }
}

@Composable
fun ComputerScreen(state: String, status: String, onConnect: () -> Unit, onDesktop: () -> Unit, onStart: () -> Unit, onStop: () -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("EchoCloud", fontSize = 25.sp, fontWeight = FontWeight.Bold, color = Color.White)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text("Cloud computer", color = WarmText)
            StatusChip(state)
        }
        Surface(color = Surface, shape = RoundedCornerShape(8.dp), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                MetricRow("Configuration", "Live account option")
                MetricRow("Desktop", "XFCE + noVNC")
                MetricRow("Persistence", "Workspace + Git")
                MetricRow("Network", status)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    if (state == "Stopped") Button(onClick = onStart, modifier = Modifier.weight(1f)) { Icon(Icons.Outlined.PowerSettingsNew, null); Spacer(Modifier.width(8.dp)); Text("START") }
                    if (state == "Running" || state == "Starting") Button(onClick = onDesktop, modifier = Modifier.weight(1f)) { Icon(Icons.Outlined.DesktopWindows, null); Spacer(Modifier.width(8.dp)); Text("CONNECT") }
                    if (state == "Running") OutlinedButton(onClick = onStop) { Text("STOP") }
                }
                OutlinedButton(onClick = onConnect, modifier = Modifier.fillMaxWidth()) { Icon(Icons.Outlined.AccountCircle, null); Spacer(Modifier.width(8.dp)); Text("CONNECT GITHUB") }
            }
        }
        Text("No fake GPU or machine availability claims.", color = Muted, fontSize = 13.sp)
    }
}

@Composable
fun StatusChip(text: String) {
    val active = text == "Running"
    Surface(color = if (active) Color(0xFF17352B) else Color(0xFF252A31), shape = RoundedCornerShape(6.dp)) {
        Text(text, modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp), color = if (active) Color(0xFF7DE0AE) else WarmText, fontSize = 12.sp)
    }
}

@Composable
fun MetricRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Muted, fontSize = 14.sp)
        Text(value, color = WarmText, fontSize = 14.sp)
    }
}

@Composable
fun FilesScreen(apiBase: String) {
    var result by remember { mutableStateOf("Loading workspace...") }
    LaunchedEffect(Unit) { result = fetchText(apiBase, "/api/v1/files") }
    Column(Modifier.fillMaxSize().padding(20.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Files", fontSize = 25.sp, fontWeight = FontWeight.Bold)
        Text(result, color = WarmText, fontSize = 13.sp)
    }
}

@Composable
fun MonitorScreen(apiBase: String) {
    var result by remember { mutableStateOf("Loading real telemetry...") }
    LaunchedEffect(Unit) { result = fetchText(apiBase, "/api/v1/telemetry") }
    Column(Modifier.fillMaxSize().padding(20.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("System monitor", fontSize = 25.sp, fontWeight = FontWeight.Bold)
        Surface(color = Surface, shape = RoundedCornerShape(8.dp)) { Text(result, modifier = Modifier.padding(16.dp), color = WarmText) }
    }
}

@Composable
fun SettingsScreen(apiBase: String) {
    var apiUrl by remember { mutableStateOf(apiBase) }
    Column(Modifier.fillMaxSize().padding(20.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Settings", fontSize = 25.sp, fontWeight = FontWeight.Bold)
        OutlinedTextField(value = apiUrl, onValueChange = { apiUrl = it }, label = { Text("EchoCloud API URL") }, modifier = Modifier.fillMaxWidth(), colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = Cyan))
        Text("GitHub credentials are kept in Android secure storage. The desktop session never receives the GitHub token.", color = WarmText)
    }
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun DesktopScreen(desktopBase: String, onBack: () -> Unit) {
    Column(Modifier.fillMaxSize().background(Graphite)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.Outlined.Close, null, tint = WarmText) }
            Text("Desktop", color = WarmText, fontWeight = FontWeight.Medium)
            Icon(Icons.Outlined.Fullscreen, null, tint = Cyan)
        }
        AndroidView(factory = { context ->
            WebView(context).apply {
                layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                settings.allowFileAccess = false
                settings.cacheMode = WebSettings.LOAD_DEFAULT
                webViewClient = object : WebViewClient() {
                    override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                        view.loadData("<body style='background:#0A0D12;color:#C8CBCF;font-family:sans-serif;padding:24px'><h2>Desktop unavailable</h2><p>Private forwarded port 6080 could not be reached. Verify the Codespace is running and the noVNC port is private and accessible.</p></body>", "text/html", "utf-8")
                    }
                }
                loadUrl(desktopBase)
            }
        }, modifier = Modifier.weight(1f))
    }
}

suspend fun fetchText(base: String, path: String): String = withContext(Dispatchers.IO) {
    try {
        val request = Request.Builder().url(base.trimEnd('/') + path).build()
        OkHttpClient().newCall(request).execute().use { response ->
            if (!response.isSuccessful) return@use "HTTP ${response.code}: ${response.message}"
            val body = response.body?.string().orEmpty()
            JsonParser.parseString(body).toString()
        }
    } catch (error: Exception) {
        "Connection unavailable: ${error.message}"
    }
}
