# auth.py
from flask import request, Response, jsonify
from functools import wraps
from werkzeug.security import check_password_hash

def check_auth(email, password, mongo):
    """Verifica se as credenciais de email e senha são válidas."""
    user = mongo.db.usuarios.find_one({'email': email})
    if user and check_password_hash(user['senha'], password):
        return True
    return False

def authenticate():
    """Envia uma resposta que solicita autenticação ao usuário."""
    response = jsonify({"login_attempt": 'FAIL'})
    response.status_code = 401
    response.headers['WWW-Authenticate'] = 'Basic realm="Login Required"'
    return response

def requires_auth(mongo):
    """Cria um decorator requires_auth com acesso à instância do mongo."""
    def requires_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or not check_auth(auth.username, auth.password, mongo):
                return authenticate()
            return f(*args, **kwargs)
        return decorated
    return requires_auth
