import grpc
import dispositivos.arquivos_pb2.servicos_dispositivos_pb2 as response_request
import dispositivos.arquivos_pb2.servicos_dispositivos_pb2_grpc as services
from google.protobuf.descriptor import FieldDescriptor  # Para mapear tipos

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
        return methods[choosed-1]
      
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

"""
    Essa lista precisa ser fornecida pelo broker.
    A lista deve conter, nesta ordem:
    [('tipo de dispositivo','id do dispositivo','ip do dispositivo', porta onde o dispositivo está rodando),(,,,),(,,,),...]
    o nome do tipo de dispositivo (que no nosso caso só pode ser lampada, televisao ou ar-condicionado)
    é importante que os nomes sigam essa exata grafia
    
"""
disp_list=[('lampada','lampada00','10.102.134.99',52692),('televisao','televisao00','10.102.134.99',52695),
           ('ar-condicionado','ar-condicionado00','10.102.134.99',52688)]

def menu(disp_list):
    print("Escolha o dispositivo que deseja usar:")
    i=1
    for disp in disp_list:
        print(f"{i}){disp[1]}")
        i=i+1
    return disp_list[int(input())-1]

if __name__ == '__main__':
    while(True):
        choosed_disp=menu(disp_list)
        client = GRPCClient(choosed_disp[2],choosed_disp[3])
        
        
        if choosed_disp[0]=="lampada":
            client.set_service(services.LampadaServiceStub)
            method=client.set_method()
            
            if method=="LigarDesligar":
                response = client.call_method('LigarDesligar', response_request.LigarDesligarRequest(interruptor=True))
                print(response.status)  
                client.close()
            elif method=="Brilho":   
                request = client.set_entries(method)
                response = client.call_method('Brilho', request)
                print(response.status) 
                client.close()
        
        if choosed_disp[0]=="televisao":
            client.set_service(services.TelevisaoServiceStub)
            method=client.set_method()
            
            if method=="LigarDesligar":
                response = client.call_method('LigarDesligar', response_request.LigarDesligarRequest(interruptor=True))
                print(response.status)  
                client.close()
            elif method=="Canal":   
                entries=client.entries_by_method_name(method)
                request = client.set_entries(method)
                response = client.call_method('Canal', request)
                print(response.status) 
                client.close()
        if choosed_disp[0]=="ar-condicionado":
            client.set_service(services.ArCondicionadoServiceStub)
            method=client.set_method()
            
            if method=="LigarDesligar":
                response = client.call_method('LigarDesligar', response_request.LigarDesligarRequest(interruptor=True))
                print(response.status)  
                client.close()
            elif method=="Temperatura":   
                entries=client.entries_by_method_name(method)
                request = client.set_entries(method)
                response = client.call_method('Temperatura', request)
                print(response.status) 
                client.close()