from pathlib import Path

pasta = Path("USP/1ª Fase")


for arquivo in pasta.iterdir():
    if not arquivo.is_file():
        continue
    ano = arquivo.stem[:4]
    file_name = f'FEVEST_{ano}_1Fase'
    if 'gab' in arquivo.stem:
        file_name += '_gab'
    print(file_name)
    arquivo.rename(arquivo.with_name(file_name+'.pdf'))