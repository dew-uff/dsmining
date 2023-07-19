import os

tamanho_total = 0
diretorio = "/home/luam/Downloads/pneumonia-detector-develop"


def obter_arquivos_recursivamente(diretorio):
    lista_arquivos = []

    for caminho_atual, _, arquivos in os.walk(diretorio):
        for arquivo in arquivos:
            caminho_completo = os.path.join(caminho_atual, arquivo)
            lista_arquivos.append(caminho_completo)

    return lista_arquivos


def obter_tamanho_arquivo(caminho_arquivo):
    tamanho_bytes = os.path.getsize(caminho_arquivo)
    tamanho_em_mb = tamanho_bytes / (1024 * 1024)

    return tamanho_em_mb


arquivos = obter_arquivos_recursivamente(diretorio)
arquivos_ordenados = sorted(arquivos, key=lambda x: obter_tamanho_arquivo(x), reverse=True)


counter = 0
for arquivo in arquivos_ordenados:
    counter = counter + 1
    tamanho_mb = obter_tamanho_arquivo(arquivo)
    tamanho_total = tamanho_total + tamanho_mb
    print("{}: {:.2f} MB".format(arquivo, tamanho_mb))

print("Number of files:", counter)
print("Média", tamanho_total/counter)
