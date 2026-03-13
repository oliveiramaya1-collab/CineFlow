import os
import requests
import random
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
    """ Função auxiliar para padronizar os dados do filme vindos da API. """
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
    query = request.args.get('search')
    res_trending = requests.get(f"{BASE_URL}/trending/movie/week", 
                                params={"api_key": API_KEY, "language": LANGUAGE})
    recomendados = [tratar_filme(f) for f in res_trending.json().get('results', [])[:5]]
    
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
        filmes = [tratar_filme(f) for f in dados.get('results', [])]
        return jsonify({"filmes": filmes})
    except Exception as e:
        return jsonify({"error": str(e), "filmes": []}), 500

@app.route('/movie/<int:movie_id>')
def detalhes(movie_id):
    endpoint = f"{BASE_URL}/movie/{movie_id}"
    params = {"api_key": API_KEY, "language": LANGUAGE, "append_to_response": "credits"}
    res = requests.get(endpoint, params=params)
    if res.status_code != 200:
        return "Filme não encontrado", 404
    dados = res.json()
    equipe = dados.get('credits', {}).get('crew', [])
    diretor = next((p['name'] for p in equipe if p['job'] == 'Director'), "Não disponível")
    elenco = [ator['name'] for ator in dados.get('credits', {}).get('cast', [])[:5]]
    generos = ", ".join([g['name'] for g in dados.get('genres', [])])
    return render_template('detalhes.html', filme=tratar_filme(dados), diretor=diretor, elenco=elenco, generos=generos)

@app.route('/minha-lista')
def minha_lista():
    return render_template('minha_lista.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/api/quiz/recomendacao')
def quiz_recomendacao():
    genero_id = request.args.get('genero')
    params = {"api_key": API_KEY, "language": LANGUAGE, "sort_by": "popularity.desc", "with_genres": genero_id, "page": 1}
    try:
        res = requests.get(f"{BASE_URL}/discover/movie", params=params)
        res.raise_for_status()
        dados = res.json()
        filmes = [tratar_filme(f) for f in dados.get('results', [])[:10]]
        return jsonify({"filmes": filmes})
    except Exception as e:
        return jsonify({"error": str(e), "filmes": []}), 500

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/api/game/questoes')
def api_game_questoes():
    todas_questoes = []
    paginas_aleatorias = random.sample(range(1, 50), 12) 
    filmes_pool = []
    for pg in paginas_aleatorias:
        try:
            res = requests.get(f"{BASE_URL}/movie/popular", params={"api_key": API_KEY, "language": LANGUAGE, "page": pg})
            if res.status_code == 200:
                filmes_pool.extend(res.json().get('results', []))
        except:
            continue
    random.shuffle(filmes_pool)
    todos_titulos_pt = [f['title'] for f in filmes_pool if f.get('title')]
    
    for filme in filmes_pool:
        if not filme.get('backdrop_path') or not filme.get('title'):
            continue
        outros_titulos = [t for t in todos_titulos_pt if t != filme['title']]
        if len(outros_titulos) < 3:
            continue
        opcoes_erradas = random.sample(outros_titulos, 3)
        opcoes = opcoes_erradas + [filme['title']]
        random.shuffle(opcoes)
        
        # Inclusão da dica no objeto enviado ao game.html
        todas_questoes.append({
            "id": filme['id'],
            "imagem": f"https://image.tmdb.org/t/p/original{filme['backdrop_path']}",
            "resposta": filme['title'],
            "opcoes": opcoes,
            "dica": f"Ano de lançamento: {filme.get('release_date', '????')[:4]}"
        })
    return jsonify(todas_questoes)

@app.errorhandler(404)
def pagina_não_encontrada(error):
    return render_template('e404.html')

@app.errorhandler(500)
def erro_de_servidor(error):
    return render_template('e500.html')

if __name__ == '__main__':
    app.run(debug=True)