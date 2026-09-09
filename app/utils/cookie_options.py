ACCESS_TOKEN_COOKIE_OPTIONS = {
    "httponly": True,
    "secure": True,
    "samesite": "none",
    "max_age": 15 * 60,  
    "path": "/",
}

REFRESH_TOKEN_COOKIE_OPTIONS = {
    "httponly": True,
    "secure": True,
    "samesite": "none",
    "max_age": 30 * 24 * 60 * 60,  
    "path": "/auth/refresh",
}
