import os


def obter_arquivos_recursivamente(diretorio):
    lista_arquivos = []

    for caminho_atual, _, arquivos in os.walk(diretorio):
        for arquivo in arquivos:
            caminho_completo = os.path.join(caminho_atual, arquivo)
            lista_arquivos.append(caminho_completo)

    return lista_arquivos


def obter_tamanho_arquivo(caminho_arquivo):
    tamanho_bytes = os.path.getsize(caminho_arquivo)
    tamanho_mb = tamanho_bytes / (1024 * 1024)

    return tamanho_mb


# Diretório que será analisado
diretorio = "path"

# Obtém todos os arquivos no diretório e subdiretórios
arquivos = obter_arquivos_recursivamente(diretorio)

# Ordena a lista de arquivos pelo tamanho em ordem decrescente
arquivos_ordenados = sorted(arquivos, key=lambda x: obter_tamanho_arquivo(x), reverse=True)


counter = 0
for arquivo in arquivos_ordenados:
    counter = counter + 1
    tamanho_mb = obter_tamanho_arquivo(arquivo)
    print("{}: {:.2f} MB".format(arquivo, tamanho_mb))

print("Number of files:", counter)
