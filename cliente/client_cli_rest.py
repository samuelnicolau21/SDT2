import requests

API_URL = "http://localhost:5000"

def listar_dispositivos():
    response = requests.get(f"{API_URL}/dispositivos")
    if response.status_code == 200:
        dispositivos = response.json()
        for i, d in enumerate(dispositivos, 1):
            print(f"{i}) {d['nome']} ({d['tipo']})")
        return dispositivos
    else:
        print("Erro ao listar dispositivos.")
        return []

def ligar_desligar(nome):
    response = requests.post(f"{API_URL}/dispositivos/{nome}/ligar_desligar")
    if response.status_code == 200:
        print(f"Status: {response.json()['status']}")
    else:
        print("Erro ao ligar/desligar o dispositivo.")

def consultar_estado(nome):
    response = requests.get(f"{API_URL}/dispositivos/{nome}/estado")
    if response.status_code == 200:
        estado = response.json()
        print("Estado do dispositivo:")
        for key, value in estado.items():
            print(f"{key}: {value}")
    else:
        print("Erro ao consultar estado.")
        
def ajustar_parametro(nome, parametro, valor):
    response = requests.post(f"{API_URL}/dispositivos/{nome}/{parametro}", json={parametro: valor})
    if response.status_code == 200:
        print(f"Status: {response.json()['status']}")
    else:
        print("Erro ao ajustar parâmetro.")

if __name__ == '__main__':
    while True:
        dispositivos = listar_dispositivos()
        if not dispositivos:
            break
        escolha = int(input("Escolha um dispositivo: ")) - 1
        if escolha < 0 or escolha >= len(dispositivos):
            print("Opção inválida.")
            continue

        nome = dispositivos[escolha]['nome']
        tipo = dispositivos[escolha]['tipo']
        print("\n1) Ligar/Desligar")
        print("2) Consultar Estado")
        if tipo == "lampada":
            print("3) Ajustar Brilho")
        elif tipo == "televisao":
            print("3) Ajustar Canal")
        elif tipo == "ar-condicionado":
            print("3) Ajustar Temperatura")
        print("4) Sair")
        opcao = input("Escolha uma opção: ")

        if opcao == "1":
            ligar_desligar(nome)
        elif opcao == "2":
            consultar_estado(nome)
        elif opcao == "3":
            if tipo == "lampada":
                valor = int(input("Digite o nível de brilho (0-100): "))
                ajustar_parametro(nome, "brilho", valor)
            elif tipo == "televisao":
                valor = int(input("Digite o número do canal (1-100): "))
                ajustar_parametro(nome, "canal", valor)
            elif tipo == "ar-condicionado":
                valor = int(input("Digite a temperatura desejada (16-30°C): "))
                ajustar_parametro(nome, "temperatura", valor)
        elif opcao == "4":
            break
        else:
            print("Opção inválida.")
