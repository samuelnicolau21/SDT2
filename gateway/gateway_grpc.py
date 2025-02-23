import sys
import os

# Adiciona o caminho da pasta 'dispositivos' ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dispositivos')))

import grpc
from google.protobuf.descriptor import FieldDescriptor  # Para mapear tipos
import dispositivos.arquivos_pb2.servicos_dispositivos_pb2 as response_request
import dispositivos.arquivos_pb2.servicos_dispositivos_pb2_grpc as services
import pika
import threading
import time
import json


# Dicionário para armazenar threads ativas
thread_dict = {}

# Lista de dispositivos registrados
disp_list = []


def callback(ch, method, properties, body):
    """Callback para processar mensagens da fila 'geral'."""
    device_info = json.loads(body.decode())  # Converte JSON para dicionário
    print(device_info)
    # Evita duplicatas pelo 'id' do dispositivo
    if device_info not in disp_list:
        disp_list.append([device_info['tipo'], device_info['id'], device_info['host'], device_info['porta']])


def leitura(ch, method, properties, body):
    """Callback para processar mensagens de uma fila específica."""
    print(f"Recebido do dispositivo: {body.decode()}")


def stop_listening(queue_name):
    """Interrompe a thread que está escutando a fila específica."""
    if queue_name in thread_dict:
        thread_info = thread_dict[queue_name]
        thread_info['stop_event'].set()  # Sinaliza para a thread parar
        thread_info['thread'].join()  # Espera a thread parar
        del thread_dict[queue_name]  # Remove a thread do dicionário
        print(f"Escuta da fila {queue_name} interrompida.")


def sign_queue(queue_name):
    """Função que escuta a fila até ser interrompida."""
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Declara a fila
    channel.queue_declare(queue=queue_name)
    channel.basic_consume(queue=queue_name, on_message_callback=leitura, auto_ack=True)

    print(f"Aguardando mensagens da fila {queue_name}...")
    stop_event = threading.current_thread().stop_event  # Evento para controlar a parada

    while not stop_event.is_set():
        try:
            channel.connection.process_data_events(time_limit=1)  # Verifica se a thread foi parada
        except Exception as e:
            print(f"Erro ao processar eventos: {e}")
            break

    # Fecha a conexão ao sair do loop
    connection.close()
    print(f"Conexão com a fila {queue_name} fechada.")


def sign_general():
    """Função que escuta a fila 'geral' para registrar dispositivos."""
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # Declara a fila 'geral'
    channel.queue_declare(queue='geral')
    channel.basic_consume(queue='geral', on_message_callback=callback, auto_ack=True)

    print("Aguardando mensagens...")
    channel.start_consuming()


class GRPCClient:
    def __init__(self, host, port):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = None

    def set_service(self, service_stub):
        self.stub = service_stub(self.channel)

    def list_method(self):
        if not self.stub:
            raise ValueError("Serviço não definido! Use set_service().")
        methods = [method for method in dir(self.stub) if not method.startswith('_')]
        for i, method in enumerate(methods, 1):
            print(f"{i}) {method}")
        return methods

    def set_method(self):
        methods = self.list_method()
        choosed = int(input("Escolha um método: "))
        return methods[choosed - 1]

    def entries_by_method_name(self, _method):
        request_class_name = _method + "Request"
        request_class = getattr(response_request, request_class_name)
        request_entries = {field.name: field for field in request_class.DESCRIPTOR.fields}
        return request_entries

    def get_python_type(self, field):
        """Mapeia tipos do Protobuf para Python"""
        proto_to_python = {
            FieldDescriptor.TYPE_BOOL: bool,
            FieldDescriptor.TYPE_INT32: int,
            FieldDescriptor.TYPE_INT64: int,
            FieldDescriptor.TYPE_FLOAT: float,
            FieldDescriptor.TYPE_DOUBLE: float,
            FieldDescriptor.TYPE_STRING: str,
        }
        return proto_to_python.get(field.type, str)  # Se não encontrado, assume string

    def set_entries(self, _method):
        request_class_name = _method + "Request"
        request_class = getattr(response_request, request_class_name)
        entries = self.entries_by_method_name(_method)

        request_data = {}
        for field_name, field in entries.items():
            python_type = self.get_python_type(field)
            value = input(f"Digite o valor de {field_name} ({python_type.__name__}): ")

            # Converte automaticamente para o tipo correto
            try:
                if python_type == bool:
                    value = value.lower() in ["true", "1", "yes", "sim"]
                else:
                    value = python_type(value)
            except ValueError:
                print(f"Erro: O valor '{value}' não pode ser convertido para {python_type.__name__}.")
                return None

            request_data[field_name] = value

        return request_class(**request_data)

    def call_method(self, method_name, request_message):
        if not self.stub:
            raise ValueError("Serviço não definido! Use set_service().")

        method = getattr(self.stub, method_name, None)
        if not method:
            raise ValueError(f"O método {method_name} não existe no serviço!")

        response = method(request_message)
        return response

    def close(self):
        """Fecha a conexão com o servidor."""
        self.channel.close()


def menu():
    """Exibe o menu e retorna a escolha do usuário."""
    global disp_list
    print("Escolha o dispositivo que deseja usar:")
    for i, disp in enumerate(disp_list, 1):
        print(f"{i}) {disp[1]}")
    print("x) Atualizar Lista")
    escolha = input()

    if escolha == 'x':
        return menu()

    escolha = int(escolha) - 1
    print("Escolha que ação relacionada a esse dispositivo você deseja:")
    print(f"1) Enviar ação para: {disp_list[escolha][1]}")
    print(f"2) Ouvir leituras do sensor de: {disp_list[escolha][1]}")
    print(f"3) Parar de ouvir leituras de: {disp_list[escolha][1]}")
    comando = int(input())

    return disp_list[escolha], comando


if __name__ == '__main__':
    t_sign_general = threading.Thread(target=sign_general)
    t_sign_general.start()

    while True:
        choosed_disp, comando = menu()
        client = GRPCClient(choosed_disp[2], choosed_disp[3])

        if comando == 1:
            # Enviar ação para o dispositivo
            if choosed_disp[0] == "lampada":
                client.set_service(services.LampadaServiceStub)
                method = client.set_method()

                if method == "LigarDesligar":
                    response = client.call_method('LigarDesligar', response_request.LigarDesligarRequest(interruptor=True))
                    print(response.status)
                elif method == "Brilho":
                    request = client.set_entries(method)
                    response = client.call_method('Brilho', request)
                    print(response.status)
                elif method == "ConsultarEstado":
                    response = client.call_method('ConsultarEstado', response_request.EmptyRequest())
                    print(f"Estado: {'Ligado' if response.ligada else 'Desligado'}, Brilho Atual: {response.brilho}")

            elif choosed_disp[0] == "televisao":
                client.set_service(services.TelevisaoServiceStub)
                method = client.set_method()

                if method == "LigarDesligar":
                    response = client.call_method('LigarDesligar', response_request.LigarDesligarRequest(interruptor=True))
                    print(response.status)
                elif method == "Canal":
                    request = client.set_entries(method)
                    response = client.call_method('Canal', request)
                    print(response.status)
                elif method == "ConsultarEstado":
                    response = client.call_method('ConsultarEstado', response_request.EmptyRequest())
                    print(f"Estado: {'Ligado' if response.ligada else 'Desligado'}, Canal Atual: {response.canalAtual}")

            elif choosed_disp[0] == "ar-condicionado":
                client.set_service(services.ArCondicionadoServiceStub)
                method = client.set_method()

                if method == "LigarDesligar":
                    response = client.call_method('LigarDesligar', response_request.LigarDesligarRequest(interruptor=True))
                    print(response.status)
                elif method == "Temperatura":
                    request = client.set_entries(method)
                    response = client.call_method('Temperatura', request)
                    print(response.status)
                elif method == "ConsultarEstado":
                    response = client.call_method('ConsultarEstado', response_request.EmptyRequest())
                    print(f"Estado: {'Ligado' if response.ligado else 'Desligado'}, Temperatura Atual: {response.temperaturaAtual}")

            client.close()

        elif comando == 2:
            # Iniciar escuta da fila do dispositivo
            queue_name = choosed_disp[1]
            if queue_name not in thread_dict:
                stop_event = threading.Event()
                thread = threading.Thread(target=sign_queue, args=(queue_name,))
                thread.stop_event = stop_event  # Adiciona o evento de parada à thread
                thread_dict[queue_name] = {'thread': thread, 'stop_event': stop_event}
                thread.start()
                print(f"Iniciando escuta da fila {queue_name}...")
            else:
                print(f"Já está escutando a fila {queue_name}.")

        elif comando == 3:
            # Parar escuta da fila do dispositivo
            queue_name = choosed_disp[1]
            stop_listening(queue_name)