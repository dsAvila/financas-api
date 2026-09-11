from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///financas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Regras de negócio
TIPOS_PERMITIDOS = ['receita', 'despesa', 'investimento']
MOEDAS_PERMITIDAS = ['BRL', 'USD']

class Transacao(db.Model):
    __tablename__ = 'transacoes'

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    moeda = db.Column(db.String(10), default='BRL')
    categoria = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'descricao': self.descricao,
            'valor': self.valor,
            'tipo': self.tipo,
            'moeda': self.moeda,
            'categoria': self.categoria
        }

with app.app_context():
    db.create_all()

def cotacao_dolar():
    """Consulta a cotação do dólar americano em tempo real"""
    try:
        url = "https://economia.awesomeapi.com.br/last/USD-BRL"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            dados = res.json()
            return float(dados['USDBRL']['bid'])
        return 5.40 # Valor de contingência caso esteja oscilando
    except Exception:
        return 5.40

# -//- Rotas API -//-

# GET
@app.route('/api/transacoes', methods=['GET'])
def listar_transacoes():
    transacoes = Transacao.query.all()
    cotacao_usd = cotacao_dolar()

    total_receitas = 0.0
    total_despesas = 0.0
    total_investimentos_brl = 0.0
    total_investimentos_usd = 0.0

    lista_transacoes = []
    for item in transacoes:
        lista_transacoes.append(item.to_dict())

        if item.tipo == 'receita':
            total_receitas += item.valor
        elif item.tipo == 'despesa':
            total_despesas += item.valor
        elif item.tipo == 'investimento':
            if item.moeda == 'USD':
                total_investimentos_usd += item.valor
            else:
                total_investimentos_brl += item.valor

    investimentos_usd_convertido = total_investimentos_usd * cotacao_usd
    saldo_caixa = total_receitas - total_despesas
    patrimonio_liquido_total = saldo_caixa + total_investimentos_brl + investimentos_usd_convertido

    return jsonify({
        'transacoes': lista_transacoes,
        'resumo': {
            'cotacao_usd': cotacao_usd,
            'saldo_caixa': round(saldo_caixa, 2),
            'investimentos_brl': round(total_investimentos_brl, 2),
            'investimentos_usd': round(total_investimentos_usd, 2),
            'investimentos_usd_em_brl': round(investimentos_usd_convertido, 2),
            'patrimonio_liquido_total': round(patrimonio_liquido_total, 2)
        }
    }), 200

# POST
@app.route('/api/transacoes', methods=['POST'])
def criar_transacao():
    dados = request.get_json()

    if not dados or not all(campo in dados for campo in ('descricao', 'valor', 'tipo', 'categoria')):
        return jsonify({'erro': 'Campos obrigatórios ausentes. Favor informar todos os campos'}), 400

    tipo = str(dados['tipo']).lower()
    moeda = str(dados.get('moeda', 'BRL')).upper()

    if tipo not in TIPOS_PERMITIDOS:
        return jsonify({
            'erro': f"Tipo inválido. Valores permitidos: {', '.join(TIPOS_PERMITIDOS)}"
        }), 400

    if moeda not in MOEDAS_PERMITIDAS:
        return jsonify({
            'erro': f"Moeda inválida. Valores permitidos: {', '.join(MOEDAS_PERMITIDAS)}"
        }), 400

    try:
        valor = float(dados['valor'])
    except ValueError:
        return jsonify({'erro': 'O campo valor deve ser numérico.'}), 400

    nova_transacao = Transacao(
        descricao = dados['descricao'],
        valor = valor,
        tipo = tipo,
        moeda = moeda,
        categoria = dados['categoria']
    )

    db.session.add(nova_transacao)
    db.session.commit()

    return jsonify(nova_transacao.to_dict()), 201

# PUT
@app.route('/api/transacoes/<int:id>', methods=['PUT'])
def atualizar_transacao(id):
    transacao = db.session.get(Transacao, id)
    if not transacao:
        return jsonify({'erro': 'Transação não encontrada'}), 404
    
    dados = request.get_json()
    if not dados:
        return jsonify({'erro': 'Dados para atualização não foram fornecidos.'}), 400

    if 'tipo' in dados:
        novo_tipo = str(dados['tipo']).lower()
        if novo_tipo not in TIPOS_PERMITIDOS:
            return jsonify({'erro': f"Tipo inválido. Valores permitidos: {', '.join(TIPOS_PERMITIDOS)}"}), 400
        transacao.tipo = novo_tipo

    if 'moeda' in dados:
        nova_moeda = str(dados['moeda']).upper()
        if nova_moeda not in MOEDAS_PERMITIDAS:
            return jsonify({'erro': f"Moeda inválida. Valores permitidos: {', '.join(MOEDAS_PERMITIDAS)}"}), 400
        transacao.moeda = nova_moeda

    transacao.descricao = dados.get('descricao', transacao.descricao)
    transacao.categoria = dados.get('categoria', transacao.categoria)

    if 'valor' in dados:
        try:
            transacao.valor = float(dados['valor'])
        except ValueError:
            return jsonify({'erro': 'O campo valor deve ser numérico.'}), 400
        
    db.session.commit()
    return jsonify(transacao.to_dict()), 200

# DELETE
@app.route('/api/transacoes/<int:id>', methods=['DELETE'])
def deletar_transacao(id):
    transacao = db.session.get(Transacao, id)
    if not transacao:
        return jsonify({'erro': 'Transação não encontrada.'}), 404

    db.session.delete(transacao)
    db.session.commit()

    return jsonify({'mensagem': f'Transação {id} removida com sucesso.'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)