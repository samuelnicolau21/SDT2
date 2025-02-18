from flask import Flask, request, jsonify
from gateway_grpc import GRPCClient  # Importa cliente gRPC
import dispositivos.arquivos_pb2.servicos_dispositivos_pb2 as response_request
import dispositivos.arquivos_pb2.servicos_dispositivos_pb2_grpc as services

app = Flask(__name__)

# Lista de dispositivos 
disp_list = [
    ('lampada', 'lampada00', 'localhost', 52164),
    ('televisao', 'televisao00', 'localhost', 52168),
    ('ar-condicionado', 'ar-condicionado00', 'localhost', 52176)
]

def get_client(dispositivo_nome):
    """Cria um cliente gRPC com base no nome do dispositivo."""
    for tipo, nome, host, porta in disp_list:
        if nome == dispositivo_nome:
            client = GRPCClient(host, porta)
            if tipo == "lampada":
                client.set_service(services.LampadaServiceStub)
            elif tipo == "televisao":
                client.set_service(services.TelevisaoServiceStub)
            elif tipo == "ar-condicionado":
                client.set_service(services.ArCondicionadoServiceStub)
            return client
    return None

@app.route('/dispositivos', methods=['GET'])
def listar_dispositivos():
    """Retorna a lista de dispositivos disponíveis."""
    return jsonify([{"tipo": d[0], "nome": d[1], "host": d[2], "porta": d[3]} for d in disp_list])

@app.route('/dispositivos/<nome>/ligar_desligar', methods=['POST'])
def ligar_desligar(nome):
    """Liga ou desliga um dispositivo."""
    client = get_client(nome)
    if not client:
        return jsonify({"erro": "Dispositivo não encontrado"}), 404

    request_message = response_request.LigarDesligarRequest(interruptor=True)
    response = client.call_method("LigarDesligar", request_message)
    client.close()
    
    return jsonify({"status": response.status})

@app.route('/dispositivos/<nome>/estado', methods=['GET'])
def consultar_estado(nome):
    """Consulta o estado de um dispositivo."""
    client = get_client(nome)
    if not client:
        return jsonify({"erro": "Dispositivo não encontrado"}), 404

    response = client.call_method("ConsultarEstado", response_request.EmptyRequest())
    client.close()

    # Retorna estado baseado no tipo de dispositivo
    estado = {"nome": nome}
    if hasattr(response, "ligada"):
        estado["ligado"] = response.ligada
    if hasattr(response, "ligado"):
        estado["ligado"] = response.ligado
    if hasattr(response, "brilho"):
        estado["brilho"] = response.brilho
    if hasattr(response, "temperaturaAtual"):
        estado["temperatura"] = response.temperaturaAtual
    if hasattr(response, "canalAtual"):
        estado["canal"] = response.canalAtual

    return jsonify(estado)

@app.route('/dispositivos/<nome>/brilho', methods=['POST'])
def setar_brilho(nome):
    """Ajusta o brilho de uma lâmpada inteligente."""
    client = get_client(nome)
    if not client:
        return jsonify({"erro": "Dispositivo não encontrado"}), 404

    brilho = request.json.get('brilho')
    if brilho is None or not (0 <= brilho <= 100):
        return jsonify({"erro": "Valor de brilho inválido. Deve estar entre 0 e 100"}), 400

    request_message = response_request.BrilhoRequest(brilho=brilho)
    response = client.call_method("Brilho", request_message)
    client.close()

    return jsonify({"status": response.status})

@app.route('/dispositivos/<nome>/canal', methods=['POST'])
def setar_canal(nome):
    """Altera o canal de uma televisão inteligente."""
    client = get_client(nome)
    if not client:
        return jsonify({"erro": "Dispositivo não encontrado"}), 404

    canal = request.json.get('canal')
    if canal is None or not (1 <= canal <= 100):
        return jsonify({"erro": "Canal inválido. Deve estar entre 1 e 100"}), 400

    request_message = response_request.CanalRequest(canalEscolhido=canal)
    response = client.call_method("Canal", request_message)
    client.close()

    return jsonify({"status": response.status})

@app.route('/dispositivos/<nome>/temperatura', methods=['POST'])
def setar_temperatura(nome):
    """Ajusta a temperatura do ar-condicionado."""
    client = get_client(nome)
    if not client:
        return jsonify({"erro": "Dispositivo não encontrado"}), 404

    temperatura = request.json.get('temperatura')
    if temperatura is None or not (16 <= temperatura <= 30):
        return jsonify({"erro": "Temperatura inválida. Deve estar entre 16 e 30 graus."}), 400

    request_message = response_request.TemperaturaRequest(temperaturaEscolhida=temperatura)
    response = client.call_method("Temperatura", request_message)
    client.close()

    return jsonify({"status": response.status})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
