import streamlit as st
import pandas as pd
import requests
import random
import re
from deep_translator import GoogleTranslator

# Configuração inicial para evitar erros de renderização
st.set_page_config(page_title="CineStream", layout="wide")

API_KEY = "8265bd1679663a7ea12ac168da84d2e8"

# Memória de sessão para evitar repetições e crashes
if 'vistos' not in st.session_state:
    st.session_state.vistos = []
if 'item_atual' not in st.session_state:
    st.session_state.item_atual = None

# Gêneros corrigidos
GENEROS_FILMES = {"Ação": 28, "Comédia": 35, "Terror": 27, "Drama": 18, "Ficção científica": 878, "Suspense": 53,
                  "Mistério": 9648, "Musical": 10402}
GENEROS_SERIES = {"Ação": 10759, "Terror/Mistério": 9648, "Sci-Fi & Fantasy": 10765, "Crime": 80, "Drama": 18,
                  "Musical": 10402}
IDS_PARA_NOMES = {v: k for k, v in {**GENEROS_FILMES, **GENEROS_SERIES}.items()}


@st.cache_data
def carregar_dados():
    try:
        df = pd.read_csv("filmes.csv", encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        return df
    except:
        return None


df = carregar_dados()


# Função de exibição isolada para evitar erros de Node
def exibir_recomendacao(item, tipo):
    translator = GoogleTranslator(source='auto', target='pt')
    titulo = item.get('title') if tipo == "movie" else item.get('name')

    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.header(f"🎬 {titulo}")

        # TAGS DE GÊNERO
        g_ids = item.get('genre_ids', [])
        tags = [IDS_PARA_NOMES.get(gid) for gid in g_ids if gid in IDS_PARA_NOMES]
        if tags: st.markdown(f"**Gêneros:** {' | '.join([f'`{t}`' for t in tags])}")

        st.write(f"📅 **Lançamento:** {item.get('release_date') or item.get('first_air_date')}")

        sinopse = item.get('overview', '')
        if not sinopse:
            d = requests.get(
                f"https://api.themoviedb.org/3/{tipo}/{item['id']}?api_key={API_KEY}&language=pt-BR").json()
            sinopse = d.get('overview', 'Sinopse não disponível.')
        st.info(f"📖 **Sinopse:**\n\n{translator.translate(sinopse)}")

        # ELENCO COM FOTOS
        c_res = requests.get(f"https://api.themoviedb.org/3/{tipo}/{item['id']}/credits?api_key={API_KEY}").json()
        cast = c_res.get('cast', [])[:5]
        if cast:
            st.subheader("👥 Elenco Principal")
            cols = st.columns(5)
            for i, actor in enumerate(cast):
                with cols[i]:
                    if actor.get('profile_path'):
                        st.image(f"https://image.tmdb.org/t/p/w185{actor['profile_path']}", use_container_width=True)
                    st.caption(actor['name'])
    with c2:
        if item.get('poster_path'):
            st.image(f"https://image.tmdb.org/t/p/w500{item['poster_path']}", use_container_width=True)


# Interface do Usuário
st.title("📺 CineStream: Filmes & Séries")

if df is not None:
    with st.sidebar:
        st.header("🎞️ Filtros")
        t_media = st.radio("Tipo:", ["Filme", "Série"])
        anos = st.slider("Anos:", 1980, 2026, (2018, 2026))
        d_gen = GENEROS_FILMES if t_media == "Filme" else GENEROS_SERIES
        g_sel = st.selectbox("Gênero:", ["Todos"] + sorted(list(d_gen.keys())))

        # Limpeza de atores
        df['cast'] = df['cast'].fillna("")
        set_atores = set()
        for linha in df['cast']:
            limpa = re.sub(r"[\[\]'\"']", "", str(linha))
            for n in limpa.split(','):
                if len(n.strip()) > 3: set_atores.add(n.strip())
        set_atores.update(["Tom Holland", "Jenna Ortega", "Finn Wolfhard", "Bill Skarsgård"])
        a_sel = st.selectbox("Ator/Atriz:", ["Todos"] + sorted(list(set_atores)))

    # ÁREA PRINCIPAL COM CONTÊINER VAZIO PARA EVITAR O CRASH
    placeholder = st.empty()

    if st.button("GERAR RECOMENDAÇÃO"):
        # Limpa o placeholder antes de gerar novo para evitar erro de Node
        placeholder.empty()

        endpoint = "movie" if t_media == "Filme" else "tv"
        params = {
            "api_key": API_KEY, "language": "pt-BR", "sort_by": "popularity.desc",
            "primary_release_date.gte" if endpoint == "movie" else "first_air_date.gte": f"{anos[0]}-01-01",
            "primary_release_date.lte" if endpoint == "movie" else "first_air_date.lte": f"{anos[1]}-12-31",
            "without_genres": "16", "with_original_language": "en"
        }

        if g_sel != "Todos": params["with_genres"] = d_gen.get(g_sel)
        if a_sel != "Todos":
            s = requests.get(f"https://api.themoviedb.org/3/search/person?api_key={API_KEY}&query={a_sel}").json()
            if s.get('results'): params["with_cast"] = s['results'][0]['id']

        res = requests.get(f"https://api.themoviedb.org/3/discover/{endpoint}", params=params).json()

        if res.get('results'):
            # LÓGICA ANTI-REPETIÇÃO: Escolhe um que não está na lista de vistos
            validos = [r for r in res['results'] if r['id'] not in st.session_state.vistos]
            if not validos:  # Se já viu tudo, reseta a lista
                st.session_state.vistos = []
                validos = res['results']

            escolhido = random.choice(validos[:10])
            st.session_state.item_atual = (escolhido, endpoint)
            st.session_state.vistos.append(escolhido['id'])
            st.rerun()

    # Exibe o conteúdo se houver algo sorteado
    if st.session_state.item_atual:
        with placeholder.container():
            exibir_recomendacao(st.session_state.item_atual[0], st.session_state.item_atual[1])
            st.balloons()