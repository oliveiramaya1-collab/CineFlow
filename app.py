import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (TMDB_API_KEY)
load_dotenv()

app = Flask(__name__)

# Configurações da API
API_KEY = os.getenv('TMDB_API_KEY')
BASE_URL = "https://api.themoviedb.org/3"
LANGUAGE = "pt-BR"

def tratar_filme(filme):
    """ 
    Função auxiliar para padronizar os dados do filme vindos da API.
    Extrai o ano da data e formata a duração se disponível.
    """
    if filme.get('release_date'):
        filme['ano'] = filme['release_date'].split('-')[0]
    
    runtime = filme.get('runtime')
    if runtime:
        horas = runtime // 60
        minutos = runtime % 60
        filme['duracao_formatada'] = f"{horas}h {minutos}min"
    
    return filme

@app.route('/')
def index():
    """
    Rota principal: Carrega os filmes do Carrossel (Trending) 
    e a primeira página do Grid Inicial.
    """
    query = request.args.get('search')
    
    # 1. Busca filmes para o Carrossel (Sempre os Trendings da semana)
    res_trending = requests.get(f"{BASE_URL}/trending/movie/week", 
                                params={"api_key": API_KEY, "language": LANGUAGE})
    # Pegamos os 5 melhores para o destaque
    recomendados = [tratar_filme(f) for f in res_trending.json().get('results', [])[:5]]
    
    # 2. Busca filmes para o Grid Inicial (Página 1)
    params_grid = {"api_key": API_KEY, "language": LANGUAGE, "page": 1}
    if query:
        endpoint = f"{BASE_URL}/search/movie"
        params_grid["query"] = query
    else:
        endpoint = f"{BASE_URL}/trending/movie/week"

    res_grid = requests.get(endpoint, params=params_grid)
    filmes_iniciais = [tratar_filme(f) for f in res_grid.json().get('results', [])]

    return render_template('index.html', filmes=filmes_iniciais, recomendados=recomendados)

@app.route('/api/filmes')
def api_filmes():
    """
    Rota de API: Usada pelo JavaScript para Pesquisa Instantânea 
    e Rolagem Infinita (Infinite Scroll). Retorna apenas JSON.
    """
    page = request.args.get('page', 1, type=int)
    query = request.args.get('search')
    
    params = {"api_key": API_KEY, "language": LANGUAGE, "page": page}
    
    if query:
        endpoint = f"{BASE_URL}/search/movie"
        params["query"] = query
    else:
        endpoint = f"{BASE_URL}/trending/movie/week"

    try:
        res = requests.get(endpoint, params=params)
        res.raise_for_status()
        dados = res.json()
        
        # Formata os filmes antes de enviar para o JavaScript
        filmes = [tratar_filme(f) for f in dados.get('results', [])]
        return jsonify({"filmes": filmes})
    except Exception as e:
        return jsonify({"error": str(e), "filmes": []}), 500

@app.route('/movie/<int:movie_id>')
def detalhes(movie_id):
    """
    Rota de Detalhes: Busca informações técnicas, elenco e direção.
    """
    endpoint = f"{BASE_URL}/movie/{movie_id}"
    params = {
        "api_key": API_KEY, 
        "language": LANGUAGE, 
        "append_to_response": "credits"
    }
    
    res = requests.get(endpoint, params=params)
    if res.status_code != 200:
        return "Filme não encontrado", 404
        
    dados = res.json()
    
    # Lógica para Diretor e Elenco
    equipe = dados.get('credits', {}).get('crew', [])
    diretor = next((p['name'] for p in equipe if p['job'] == 'Director'), "Não disponível")
    elenco = [ator['name'] for ator in dados.get('credits', {}).get('cast', [])[:5]]
    generos = ", ".join([g['name'] for g in dados.get('genres', [])])
    
    return render_template('detalhes.html', 
                           filme=tratar_filme(dados), 
                           diretor=diretor, 
                           elenco=elenco, 
                           generos=generos)

@app.route('/minha-lista')
def minha_lista():
    """ Rota para a página de favoritos (gerida pelo LocalStorage no navegador) """
    return render_template('minha_lista.html')

#Rota do ERRO 404
@app.errorhandler(404)
def pagina_não_encontrada(error):
    return render_template('e404.html')

# Rota do ERRO 500
@app.errorhandler(500)
def erro_de_servidor(error):
    return render_template('e500.html')

if __name__ == '__main__':
    # Rodar o app em modo debug para facilitar o desenvolvimento
    app.run(debug=True)