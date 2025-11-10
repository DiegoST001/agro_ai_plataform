from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.http import JsonResponse, HttpResponse

def health_check(request):
    return JsonResponse({"status": "ok"})

def ascii_home(request):
    html = """
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>AGRONIX</title>
<style>
  :root {
    --bg: #0b0f1a;
    --fg: #e6f0ff;
  }
  html,body{height:100%}
  body{
    margin:0; display:flex; align-items:center; justify-content:center;
    background: radial-gradient(1200px 800px at 50% 40%, #121a2b 0%, #0b0f1a 60%, #06080f 100%);
    color: var(--fg); overflow:hidden; font-family: "Courier New", ui-monospace, monospace;
  }
  .wrap{ text-align:center; }
  .logo{
    white-space: pre; line-height:1.05; letter-spacing: 1px;
    font-size: clamp(10px, 2.2vw, 22px);
    background: linear-gradient(90deg,#ff0066,#ffcc00,#33cc33,#00ccff,#9933ff,#ff0066);
    background-size: 400% 100%;
    -webkit-background-clip: text; background-clip: text; color: transparent;
    animation: gradientMove 8s linear infinite;
    filter: drop-shadow(0 0 10px rgba(0,200,255,.15));
    user-select: none;
  }
  .subtitle{
    margin-top:16px; opacity:.85; font-size: clamp(12px, 1.3vw, 18px);
    letter-spacing:.2em;
    animation: pulse 3s ease-in-out infinite;
  }
  .scanline::after{
    content:""; position:fixed; left:0; right:0; top:-100%;
    height:120%; background: linear-gradient( to bottom,
      rgba(255,255,255,0) 0%,
      rgba(255,255,255,0.05) 50%,
      rgba(255,255,255,0) 100%);
    animation: scan 5s linear infinite;
    pointer-events:none;
  }
  @keyframes gradientMove { 0%{background-position:0% 50%} 100%{background-position:100% 50%} }
  @keyframes pulse { 0%,100%{opacity:.7} 50%{opacity:1} }
  @keyframes scan { 0%{top:-100%} 100%{top:100%} }
  .links{ margin-top: 18px; }
  .links a{
    color:#9ad3ff; text-decoration:none; margin:0 10px; opacity:.9;
  }
  .links a:hover{ text-decoration:underline; opacity:1 }
</style>
</head>
<body class="scanline">
  <div class="wrap">
<pre class="logo">
  █████╗   ██████╗  ██████╗  ██████╗  ███╗   ██╗ ██╗ ███╗  ██╗ ██╗
 ██╔══██╗ ██╔════╝ ██╔═══██╗██╔═══██╗ ████╗  ██║ ██║ ████╗ ██║ ██║
 ███████║ ██║      ██║   ██║██║   ██║ ██╔██╗ ██║ ██║ ██╔██╗██║ ██║
 ██╔══██║ ██║      ██║   ██║██║   ██║ ██║╚██╗██║ ██║ ██║╚████║ ██║
 ██║  ██║ ╚██████╗ ╚██████╔╝╚██████╔╝ ██║ ╚████║ ██║ ██║ ╚███║ ██║
 ╚═╝  ╚═╝  ╚═════╝  ╚═════╝  ╚═════╝  ╚═╝  ╚═══╝ ╚═╝ ╚═╝  ╚══╝ ╚═╝
</pre>
    <div class="subtitle">Agro AI Platform</div>
    <div class="links">
      <a href="/api/docs/">Docs</a> ·
      <a href="/api/schema/">OpenAPI</a> ·
      <a href="/healthz/">Health</a>
    </div>
  </div>
</body>
</html>
"""
    return HttpResponse(html, content_type="text/html")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),

    # API apps
    path('api/', include('parcels.urls')),
    path('api/', include('plans.urls')),
    path('api/', include('recommendations.urls')),
    path('api/', include('nodes.urls')),
    path('api/', include('tasks.urls')),
    path('api/', include(('crops.urls', 'crops'), namespace='crops')),
    path('api/admin/', include('users.admin_urls')),
    path('api/rbac/', include('users.rbac_urls')),
    path('api/user/', include('users.user_urls')),
    path("api/ai/", include("ai.urls")),
    path('api/brain/', include('brain.urls')),

    # OpenAPI / docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Landing y health check
    path('', ascii_home),           # raíz con ASCII animado
    path('healthz/', health_check), # endpoint para Render
]
