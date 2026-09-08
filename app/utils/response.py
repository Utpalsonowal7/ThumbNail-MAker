def success_response(message: str, data=None):
    return {"success": True, "message": message, "data": data}
