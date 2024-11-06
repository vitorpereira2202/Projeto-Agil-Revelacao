from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re

from apscheduler.schedulers.blocking import BlockingScheduler
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


app = Flask(__name__)
load_dotenv('.cred')
app.config["MONGO_URI"] = os.getenv('MONGO_URI', 'localhost')
smtp_server = 'smtp.gmail.com'
smtp_port = 587
email_remetente = "aquafinder.insper@gmail.com"
senha = "uzvx phud uqzl jkay"

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


# PREDIOS
@app.route('/predios', methods=['GET'])
def listar_predios():
    documentos = mongo.db.aquarios.find({}, {'predio': 1})
    predios = [doc['predio'] for doc in documentos]
    return jsonify({'predios': predios}), 200

# AQUARIOS

@app.route('/predios/<predio>', methods=['GET'])
def listar_aquarios_por_predio(predio):
    documento = mongo.db.aquarios.find_one({'predio': predio.upper()})
    if not documento:
        return jsonify({'msg': 'Prédio não encontrado'}), 404
    
    resultado = []
    for andar in sorted(documento['andares'], key=lambda x: x['andar']):
        aquarios_info = {
            'andar': andar['andar'],
            'aquarios': andar['aquarios']
        }
        resultado.append(aquarios_info)
    return jsonify(resultado), 200

# AQUARIO OCUPAR/DESOCUPAR
@app.route('/aquarios/ocupar/<predio>/<int:andar>/<int:numero>', methods=['PUT'])
def ocupar_aquario(predio, andar, numero):
    predio = predio.upper()
    
    result = mongo.db.aquarios.update_one(
        {'predio': predio},
        {'$set': {'andares.$[andarElem].aquarios.$[aquarioElem].ocupado': True}},
        array_filters=[
            {'andarElem.andar': andar},
            {'aquarioElem.numero': numero, 'aquarioElem.ocupado': False}
        ]
    )
    
    if result.modified_count == 0:
        return jsonify({'msg': 'Aquário não encontrado ou já está ocupado'}), 400
    
    return jsonify({'msg': 'Aquário ocupado com sucesso'}), 200


@app.route('/aquarios/desocupar/<predio>/<int:andar>/<int:numero>', methods=['PUT'])
def desocupar_aquario(predio, andar, numero):
    predio = predio.upper()
    
    
    result = mongo.db.aquarios.update_one(
        {'predio': predio},
        {'$set': {'andares.$[andarElem].aquarios.$[aquarioElem].ocupado': False}},
        array_filters=[
            {'andarElem.andar': andar},
            {'aquarioElem.numero': numero, 'aquarioElem.ocupado': True}
        ]
    )
    
    if result.modified_count == 0:
        return jsonify({'msg': 'Aquário não encontrado ou já está desocupado'}), 400
    
    return jsonify({'msg': 'Aquário desocupado com sucesso'}), 200








def formatar_aquarios_disponiveis(aquariosp1, aquariosp2, aquariosp4):
    def listar_aquarios_disponiveis(predios, predio_nome):
        aquarios_disponiveis = []
        for predio in predios:
            for andar in predio.get("andares", []):
                andar_numero = andar['andar']
                for aquario in andar.get("aquarios", []):
                    if not aquario["ocupado"]:  
                        aquarios_disponiveis.append(f"Andar {andar_numero} - Aquário {aquario['numero']}")
        return f"{predio_nome}: " + ", ".join(aquarios_disponiveis) if aquarios_disponiveis else f"{predio_nome}: Nenhum disponível"

   
    p1_disponiveis = listar_aquarios_disponiveis(aquariosp1, "P1")
    p2_disponiveis = listar_aquarios_disponiveis(aquariosp2, "P2")
    p4_disponiveis = listar_aquarios_disponiveis(aquariosp4, "P4")
    return f"Aquários disponíveis:\n{p1_disponiveis}\n{p2_disponiveis}\n{p4_disponiveis}"



def enviar_email():
        
    usuarios = list(mongo.db.usuarios.find({}, {'email': 1}))
    aquariosp1 = list(mongo.db.aquarios.find({'predio': 'P1'}, {'andares':1}))
    aquariosp2 = list(mongo.db.aquarios.find({'predio': 'P2'}, {'andares':1}))
    aquariosp4 = list(mongo.db.aquarios.find({'predio': 'P4'}, {'andares':1}))

    users = [usuario['email'] for usuario in usuarios]
    corpo_mensagem = formatar_aquarios_disponiveis(aquariosp1, aquariosp2, aquariosp4)


    for usuario in usuarios:
        users.append(usuario['email'])


   
    mensagem = MIMEMultipart()
    mensagem["From"] = email_remetente
    mensagem["To"] = ", ".join(users)
    mensagem["Subject"] = "Disponibilidade dos aquários"
    mensagem.attach(MIMEText(corpo_mensagem, "plain"))

    try:
      
        servidor = smtplib.SMTP(smtp_server, smtp_port)
        servidor.starttls()  
        servidor.login(email_remetente, senha)
        servidor.sendmail(email_remetente, users, mensagem.as_string())
        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
    finally:
        servidor.quit()
    

def enviar_email_automatico():
    with app.app_context():
        enviar_email()


def iniciar_scheduler():
    scheduler = BlockingScheduler()
    scheduler.add_job(enviar_email_automatico, 'interval', minutes = 30)  


    try:
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        
        print("Não foi possivel verificar o site")



if __name__ == '__main__':

    threading.Thread(target=iniciar_scheduler).start()
    app.run(debug=True)

