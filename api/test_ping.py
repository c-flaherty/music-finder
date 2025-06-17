import json

def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

def handler(request):
    if request.method == "OPTIONS":
        return ("", 204, _cors_headers())
    return (
        json.dumps({"ok": True, "method": request.method}),
        200,
        {"Content-Type": "application/json", **_cors_headers()},
    ) 