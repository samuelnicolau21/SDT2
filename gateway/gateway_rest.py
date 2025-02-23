import sys
import os

# Adiciona o caminho da pasta 'dispositivos' ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dispositivos')))

from flask import Flask, request, jsonify
from gateway.gateway_grpc import GRPCClient  # Importa cliente gRPC
import dispositivos.arquivos_pb2.servicos_dispositivos_pb2 as response_request
import dispositivos.arquivos_pb2.servicos_dispositivos_pb2_grpc as services
import pika
import threading
import json

app = Flask(__name__)


disp_list = []
thread_dict_listening = {'nome_thread':"", 'thread': None, 'stop_event': None}
thread_dict_consuming = {'nome_thread':"", 'thread': None, 'stop_event': None}
L = ""
ja_escutando = 0

def callback(ch, method, properties, body):
    """Callback para processar mensagens da fila 'geral'."""
    device_info = json.loads(body.decode())  # Converte JSON para dicionário
    print(f"Dispositivo registrado: {device_info}")
    # Evita duplicatas pelo 'id' do dispositivo
    if device_info not in disp_list:
        disp_list.append([device_info['tipo'], device_info['id'], device_info['host'], device_info['porta']])


def leitura(ch, method, properties, body, stop_event):
    """Callback para processar mensagens de uma fila específica."""
    if stop_event.is_set():
        print("Parando a escuta...")
        ch.stop_consuming()  # Interrompe o consumo se o evento foi setado
    else:
        dispositivo_nome = method.routing_key  # Assumindo que o nome do dispositivo é o nome da fila
        global L
        L = body.decode()
        print(f"Leitura recebida do dispositivo {dispositivo_nome}: {L}")


def stop_listening(nome):
    global thread_dict_listening
    global thread_dict_consuming
    """Função que interrompe a escuta da fila de um dispositivo.""" 
    if thread_dict_listening['nome_thread']==nome:
        thread_info = thread_dict_listening
        if 'thread' in thread_info:  # Verifica se a chave 'thread' existe
            thread_info['stop_event'].set()  #parando a thread de escutar a queue_name
            thread_info['thread'].join()
            thread_info = thread_dict_consuming
            thread_info['stop_event'].set()  #parando a thread de consumir a queue_name
            thread_info['thread'].join()
            print(f"Escuta da fila {nome} parada.")
            
        else:
            print(f"Nenhuma thread associada ao dispositivo {nome}.")
    else:
        print(f"Dispositivo {nome} não encontrado.")

def listen_to_queue(channel, stop_event):
    channel.start_consuming()


def sign_queue(queue_name):
    global thread_dict_consuming
    """Função que escuta a fila até ser interrompida.""" 
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Declara a fila
    channel.queue_declare(queue=queue_name)
    # Evento de parada da thread
    stop_event = threading.Event()

    # Registra o callback para processar as mensagens
    channel.basic_consume(queue=queue_name, on_message_callback=lambda ch, method, properties, body: leitura(ch, method, properties, body, stop_event), auto_ack=True)

    # Cria a thread para escutar a fila
    thread = threading.Thread(target=listen_to_queue, args=(channel, stop_event))
    thread.start()
    print(f"Aguardando mensagens da fila {queue_name}...")
    thread_dict_consuming= {'nome_thread':queue_name, 'thread': thread, 'stop_event': stop_event}


def sign_general():
    """Função que escuta a fila 'geral' para registrar dispositivos."""
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Declara a fila 'geral'
    channel.queue_declare(queue='geral')
    channel.basic_consume(queue='geral', on_message_callback=callback, auto_ack=True)

    print("Aguardando mensagens...")
    channel.start_consuming()


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


def iniciar_escuta(nome):
    global thread_dict_listening
    """Inicia a escuta da fila de leituras de um dispositivo.""" 
    if thread_dict_listening['nome_thread']!=nome:
        stop_event = threading.Event()
        thread = threading.Thread(target=sign_queue, args=(nome,))
        thread.stop_event = stop_event  # Adiciona o evento de parada à thread
        thread_dict_listening= {'nome_thread':nome, 'thread': thread, 'stop_event': stop_event}
        thread.start()
        print(f"Escuta da fila {nome} iniciada.")
    else:
        print(f"Já está escutando a fila {nome}.")


@app.route('/dispositivos/<nome>/parar_ouvir', methods=['POST'])
def parar_escuta(nome):
    global thread_dict_listening
    """Interrompe a escuta da fila de leituras de um dispositivo.""" 
    print(f"Nome da fila que quero parar de escutar:{nome}")
    print(f"Nome da fila registrada no dicioário de escutadores:{thread_dict_listening['nome_thread']}")
    if thread_dict_listening['nome_thread']==nome:
        stop_listening(nome)
        global ja_escutando
        ja_escutando = 0
        thread_dict_consuming={'nome_thread': "", 'thread': None, 'stop_event': None}
        thread_dict_listening={'nome_thread': "", 'thread': None, 'stop_event': None}
        return jsonify({"status": f"Escuta da fila {nome} interrompida."}), 200
    else:
        return jsonify({"erro": f"Não há escuta ativa para a fila {nome}."}), 404


@app.route('/dispositivos/<nome>/leituras', methods=['GET'])
def obter_leituras(nome):
    global ja_escutando
    global L
    """Retorna as leituras mais recentes de um dispositivo.""" 
    if ja_escutando == 0:
        iniciar_escuta(nome)
        ja_escutando = 1
    return jsonify({f"{nome}": L})


if __name__ == '__main__':
    # Inicia a thread para escutar a fila 'geral' e registrar dispositivos
    t_sign_general = threading.Thread(target=sign_general)
    t_sign_general.start()

    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
