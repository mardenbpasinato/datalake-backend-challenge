# Overview

Este projeto foi divido em duas partes (part_1 e parte_2) de acordo com os dois itens solicitados. Em ambos os casos, foi utilizado [docker](https://docs.docker.com/install/) e [docker-compose](https://docs.docker.com/compose/) para montar a arquitetura das soluções, ou seja, cada diretório possui um arquivo *docker-compose.yml* onde estão descritos os componentes e a forma como eles interoperam.

Caso não possua o *docker* ou o *docker-compose*, os links acima podem guiar-lhe no processo de instalação. O *docker* e o *docker-compose* permitem que as soluções aqui apresentadas sejam executadas nos ambientes *Linux*, *Windows* e *Mac*.

# Parte 1

## Estratégia

Optou-se por criar uma api que recebe o pacote, em formato json, gera um hash do mesmo e armazena esse hash em um servidor de cache pelo tempo desejado. Desta forma, requisições cujo hash seja igual a um dos armazenados serão devidamente rejeitadas.

Como o conteúdo do pacote não é necessário, decidiu-se por armazenar apenas o hash do mesmo. Isto trará uma economia de espaço no servidor de cache, uma vez que o pacote json pode chegar a alguns Gb de tamanho.

Os hashes serão armazenados em um servidor de cache compartilhado, o que permite que a aplicação seja replicada, para fins de escalabilidade, e todas as instâncias continuem tendo acesso aos dados (serão *stateless*).

Além disso, caso ocorra um pico de requisições com pacotes distintos, se a aplicação fosse acessar o banco diretamente poderia causar uma sobrecarga no mesmo. Logo, para amortizar este pico de inserções, a api irá inserir o pacote em uma fila e um processo assíncrono irá consumir desta fila e executar a inserção no banco.

## Componentes

* **api**: aplicação em [Flask](http://flask.pocoo.org/) responsável por receber a requisição, gerar o hash do pacote json e verificar se o mesmo está armazenado no cache. Caso não esteja, insere o pacote na fila para inserção no banco.

* **worker**: processo assíncrono, escrito em [Celery](http://www.celeryproject.org/), responsável consumir o pacote da fila e executar a inserção do mesmo no banco.

* **nginx**: balanceador de carga responsável por rotear as requisções entre as várias instâncias de **api**.

* **redis**: servidor de cache responvável por armazenar os hashes por um período determinado.

* **mongodb**: banco responsável por armazenar os pacotes json de forma durável.

* **rabbitmq**: fila responsável por amortizar as solicitações de inserção no banco.

* **redis-commander**: ferramenta para inspecionar o cache.

* **nosqlclient**: ferramenta para inspecionar o banco.

## Executando

Para levantar o projeto:

```bash
# Visualizando os logs dos componentes
docker-compose up

# Rodando os componentes em background
docker-compose up -d

#PS: O componente do rabbitmq demora um pouco para subir. Caso receba um erro na primeira requisição, aguarde alguns instantes.
```

Acessando a api:

```bash
# Enviando um json inválido
curl -X POST http://localhost:8000/v1/products -d '[{"id": "123", "name": "mesa"' #=> 400

# Enviando um json válido
curl -X POST http://localhost:8000/v1/products -d '[{"id": "123", "name": "mesa"}]' #=> 200

# Enviando o mesmo json dentro de um intervalo de 10 minutos
curl -X POST http://localhost:8000/v1/products -d '[{"id": "123", "name": "mesa"}]' #=> 403

# Enviando o mesmo json após 10 minutos
curl -X POST http://localhost:8000/v1/products -d '[{"id": "123", "name": "mesa"}]' #=> 200
```

## Inspecionando

### Redis

Para acessar a ferramenta de inspeção do redis, basta acessar http://localhost:8081/.

### RabbitMQ

Para acessar a ferramenta de inspeção do rabbitmq, acesse http://localhost:15672/, com usuário `guest` e senha `guest`.

### MongoDB

Para acessar a ferramenta de inspeção do mongodb, acesse http://localhost:3000/, crie uma conexão com hostname `mongodb`, porta `27017` e database `challenge`. Dê o nome que preferir para a conexão.

## Rodando Testes

Para executar os testes de **api**, acesse o container e execute a bateria de testes:

```bash
# Para saber o nome do container rode o comando: 
docker ps

# Para acessar o container, rode o comando:
docker exec -it part1_api_1 sh

# Para executar os testes, rode os comandos:
coverage run -m pytest -vv
coverage report
```

Para executar os testes de **worker**, acesse o container e execute a bateria de testes:

```bash
# O componente worker possui nome fixo: worker 
docker exec -it worker sh

# Para executar os testes, rode os comandos:
coverage run -m pytest -vv
coverage report
```

## Escalando

Para escalar o componente **api**, levante o projeto com o seguinte commando:

```bash
# Criando 5 instâncias de api
docker-compose up --scale api=5

# Criando 5 instâncias de api em modo background
docker-compose up --scale api=5 -d

#PS: O componente do rabbitmq demora um pouco para subir. Caso receba um erro na primeira requisição, aguarde alguns instantes.
```

## Finalizando

Para encerrar o projeto, execute o seguinte comando:

```bash
docker-compose down
```

# Parte 2

## Estratégia

Optou-se por criar um processo assíncrono que consome de uma fila cada linha do arquivo (pacote com ID do produto e URL da imagem), verifica em uma memória compartilhada se, para aquele produto, a imagem já não foi acessada junto ao servidor de imagens. 

Caso já conste um acesso para aquela imagem, não é preciso acessar o servidor de imagem novamente. Caso contrário, efetua-se uma requisição e armazena-se a informação (se a imagem existe ou não) na memória compartilhada.

Desta forma, pode-se escalar o processo consumidor em várias instâncias, executando este processamento de forma distribuída entre as várias instâncias e aumentando a vazão da fila.

Será preciso, no entanto, dois processos auxiliares. O primeiro deverá ler o(s) arquivo(s) de entrada e enviar suas linhas como pacotes para fila de processamento. Esvaziada a fila, isto é, todas as linhas já foram devidamente processadas, será preciso um processo que leia da memória compartilha e consolide as informaçoes ali contidas para o arquivo de saída.

## Componentes

* **worker**: aplicação escrita em [Celery](http://www.celeryproject.org/) que irá consumir da fila e verificar se a imagem já foi acessada. Caso não tenha sido, irá acessá-la e armazenar o resultado na memória compartilhada.

* **scripts**: servidor que contem os dois processos auxiliares: `startup.py` e `consolidate.py`. O primeiro, vasculha a o diretório `/data/input` e, para todo arquivo ali contido, abre-o e envia suas linhas como pacotes para a fila. Ao finalizar, move-os para o diretório `/data/processed`. O segundo, que deve ser executado somente após a fila esvaziar, consolida as informações contidas em memória e salva-as em um arquivo, cujo nome segue o formato `YYYY_MM_DD-HH_MM_SS-output-dump`, no diretório `/data/output`. 

* **mock**: servidor de imagem que será acessado e responderá se a imagem existe ou não.

* **redis**: servidor de memória compartilhada responsável por armazenar as informações sobre a existência ou não das imagens.

* **rabbitmq**: servidor de fila responsável por distribuir os pacotes entre as instâncias de **worker**.

* **redis-commander**: ferramenta para inspecionar a memória compartilhada.

## Executando

Para levantar o projeto:

```bash
# Visualizando os logs dos componentes
docker-compose up

# Rodando os componentes em background
docker-compose up -d

#PS: O componente do rabbitmq demora um pouco para subir. Caso receba um erro logo no início, aguarde alguns instantes.
```

Inicializando o processamento:

```bash
# Acesse o container scripts (nome fixo)
docker exec -it scripts sh

# Inicie o envio dos pacotes para a fila
python startup.py

# Após todos os pacotes terem sido processados, inicie a consolidação
python consolidate.py
```

## Inspecionando

### Redis

Para acessar a ferramenta de inspeção do redis, basta acessar http://localhost:8081/.

### RabbitMQ

Para acessar a ferramenta de inspeção do rabbitmq, acesse http://localhost:15672/, com usuário `guest` e senha `guest`.

## Rodando Testes

Para executar os testes de **worker**, acesse o container e execute a bateria de testes:

```bash
# Para saber o nome do container rode o comando: 
docker ps

# Para acessar o container, rode o comando:
docker exec -it part2_worker_1 sh

# Para executar os testes, rode os comandos:
coverage run -m pytest -vv
coverage report
```

## Escalando

Para escalar o componente **worker**, levante o projeto com o seguinte commando:

```bash
# Criando 5 instâncias de worker
docker-compose up --scale worker=5

# Criando 5 instâncias de api em modo background
docker-compose up --scale worker=5 -d

#PS: O componente do rabbitmq demora um pouco para subir. Caso receba um erro logo no início, aguarde alguns instantes.
```

## Finalizando

Para encerrar o projeto, execute o seguinte comando:

```bash
docker-compose down
```