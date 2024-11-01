from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
load_dotenv('.cred')
app.config["MONGO_URI"] = os.getenv('MONGO_URI', 'localhost')
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
    
    # Atualiza o campo 'ocupado' do aquário especificado para True
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
    
    # Atualiza o campo 'ocupado' do aquário especificado para False
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

if __name__ == '__main__':
    app.run(debug=True)
