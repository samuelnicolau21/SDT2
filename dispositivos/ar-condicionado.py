import grpc
from concurrent import futures
import arquivos_pb2.servicos_dispositivos_pb2 as response_request
import arquivos_pb2.servicos_dispositivos_pb2_grpc as services
import pika
import random
import time
import json
import threading
import logging


# Variáveis globais
ip = "localhost"
porta = 0
id_ = "ar-condicionado00"
estado = "desligado"
temperatura = 24.0
temperatura_ambiente = 24.0


class ArCondicionadoService(services.ArCondicionadoServiceServicer):
    def LigarDesligar(self, request, context):
        global estado
        estado = "ligado" if estado == "desligado" else "desligado"
        logging.info(f"Estado alterado para {estado}")
        return response_request.StatusResponse(status=f"Estado alterado para {estado}")

    def Temperatura(self, request, context):
        global temperatura
        temperatura = request.temperaturaEscolhida
        logging.info(f"Temperatura alterada para {temperatura}°C")
        return response_request.StatusResponse(status=f"Temperatura alterada para {temperatura}°C")

    def ConsultarEstado(self, request, context):
        logging.info(f"Consultando estado: Ligado={estado == 'ligado'}, Temperatura={temperatura}°C")
        return response_request.ArCondicionadoEstadoResponse(ligado=(estado == "ligado"), temperaturaAtual=temperatura)


def serve():
    global porta, id_
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    services.add_ArCondicionadoServiceServicer_to_server(ArCondicionadoService(), server)
    port_bind = server.add_insecure_port('[::]:0')
    porta = port_bind
    server.start()
    logging.info(f"Servidor {id_} rodando na porta {porta}...")

    id_ = input("Digite o id do dispositivo sensor: ")
    queue_name = id_
    sensor_register(queue_name)

    # Inicia a thread para publicar mensagens
    t_publish_on_my_queue = threading.Thread(target=publish_message_on_my_queue, args=(queue_name,), daemon=True)
    t_publish_on_my_queue.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logging.info("Servidor encerrado.")


def sensor_register(queue_name):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='geral')

        device_info = {
            'id': id_,
            'tipo': 'ar-condicionado',
            'host': ip,
            'porta': porta
        }

        message = json.dumps(device_info)
        channel.basic_publish(exchange='', routing_key='geral', body=message)
        logging.info(f"Sensor registrado: {queue_name}")
        connection.close()
    except Exception as e:
        logging.error(f"Erro ao registrar sensor: {e}")


def publish_message_on_my_queue(queue_name):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue=queue_name)

        while True:
            varia_temperatura()
            message = f'{temperatura_ambiente}°C'
            channel.basic_publish(exchange='', routing_key=queue_name, body=message)
            logging.info(f"Mensagem enviada: {message}")
            time.sleep(10)
    except Exception as e:
        logging.error(f"Erro ao publicar mensagem: {e}")
    finally:
        connection.close()


def varia_temperatura():
    global temperatura_ambiente
    global temperatura
    ale=random.uniform(0,1)
    
    if ale > 0.5:
        temperatura_ambiente=temperatura+temperatura_ambiente*round(random.uniform(0, 2), 2)
    elif ale<=0.5:
       temperatura_ambiente=temperatura-temperatura_ambiente*round(random.uniform(0, 2), 2)
    temperatura_ambiente = round(temperatura, 2)  # Garante que a temperatura tenha 2 casas decimais


if __name__ == '__main__':
    serve()