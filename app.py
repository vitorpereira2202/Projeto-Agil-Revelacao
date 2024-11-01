from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re
from flask_mail import Mail, Message
from apscheduler.schedulers.blocking import BlockingScheduler
import threading


app = Flask(__name__)
load_dotenv('.cred')
app.config["MONGO_URI"] = os.getenv('MONGO_URI', 'localhost')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'aquafinder.insper@gmail.com'
app.config['MAIL_PASSWORD'] = 'xipx disj wkeg gwyt'
app.config['MAIL_DEFAULT_SENDER'] = 'aquafinder.insper@gmail.com'

mail = Mail(app)
mongo = PyMongo(app)



# USUARIOS

@app.route('/cadastro', methods=['POST'])
def cadastro():
    dados = request.json
    email = dados.get('email')
    senha = dados.get('senha')

    if not email or not senha:
        return jsonify({'msg': 'Email e senha são obrigatórios'}), 400

    # Verifica se o usuário já existe
    if mongo.db.usuarios.find_one({'email': email}):
        return jsonify({'msg': 'Usuário já existe'}), 400
    
    # Validação se email eh do insper
    if not re.match(r'^.+@(al\.insper\.edu\.br|insper\.edu\.br)$', email):
        return jsonify({'msg': 'Email inválido. Use um email institucional do Insper.'}), 400

    # Hash seguro da senha
    hashed_senha = generate_password_hash(senha, method='pbkdf2:sha256', salt_length=16)

    # Insere o novo usuário no banco de dados
    mongo.db.usuarios.insert_one({'email': email, 'senha': hashed_senha})

    return jsonify({'msg': 'Usuário registrado com sucesso'}), 201


@app.route('/login', methods=['POST'])
def login():
    dados = request.json
    email = dados.get('email')
    senha = dados.get('senha')

    if not email or not senha:
        return jsonify({'msg': 'Email e senha são obrigatórios'}), 400

    user = mongo.db.usuarios.find_one({'email': email})

    if user and check_password_hash(user['senha'], senha):
        return jsonify({'msg': 'Login bem-sucedido'}), 200
    
    else:
        return jsonify({'msg': 'Credenciais inválidas'}), 401


# AQUARIOS













































































































































































































































def enviar_email():
    try:
        user = mongo.db.usuarios.find_all({},{'email': 1})
        aquarios = mongo.db.aquarios.find_all({})
        msg = Message(
            "Disponibilidade de aquário",
            recipients= [user],
            body= f"Os aquarios {aquarios} estão disponíveis!"
        )
        mail.send(msg)
        return "E-mail enviado com sucesso!"
    except Exception as e:
        return f"Erro ao enviar e-mail: {str(e)}"


def enviar_email_automatico():
    with app.app_context():
        enviar_email()



def iniciar_scheduler():
    scheduler = BlockingScheduler()
    scheduler.add_job(enviar_email_automatico, 'interval', minutes = 1)  


    try:
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        
        print("Não foi possivel verificar o site")


if __name__ == '__main__':
    threading.Thread(target=iniciar_scheduler).start()
    app.run(debug=True)