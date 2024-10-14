import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from jinja2 import Template


#http://127.0.0.1:80004

app = FastAPI()

@app.get("/")
def index():
    return {"Sistema Recomendacion STEAM"}

# Devuelve la cantidad de items y porcentaje de contenido Free por año para la empresa desarrolladora ingresada como
# parametro.
@app.get("/developer/{desarrollador}")
def developer(desarrollador : str):

    df_dev = pd.read_parquet('Archivos API/def_developer.parquet')
    dev = df_dev[df_dev['developer']==desarrollador]
    dev['free']=dev['price'].apply(lambda x: 1 if x == 0 else 0)
    dev['tot']=1
    dev = dev.groupby(['developer','release_year']).agg({'free': 'sum','tot':'count'}).reset_index()
    dev['percentage']=((dev['free']/dev['tot'])*100).round(2)
    dev.drop(columns=['developer','free'],inplace=True)
    dev.rename(columns={'release_year':'Año','tot':'Cantidad de items','percentage':'Contenido Free (%)'},inplace=True)
    
    # Usar Jinja2 para renderizar la tabla dentro de una plantilla HTML
    template = Template("""
    <html>
    <head><title>Tabla de Datos</title></head>
    <body>
        {{ table_html | safe }}
    </body>
    </html>
    """)
    
    # Renderizar la plantilla con los datos
    html_content = template.render(table_html=dev.to_html())

    return HTMLResponse(content=html_content)
    #return dev.to_dict(orient='records')


# Devuelve la cantidad de dinero gastado por el usuario ingresado como parametro, el porcentaje de recomendación en 
# base a reviews.recommend y cantidad de items.
@app.get("/userdata/{user_id}")
def userdata(user_id : str):

    df_user = pd.read_parquet('Archivos API/def_userdata.parquet')
    u_data = df_user[df_user['user_id']==user_id]

    return {"User":user_id,"Dinero gastado":float(u_data['price'].sum()),
            "% Recomendacion":(u_data[u_data['recommend']].shape[0]/u_data.shape[0])*100,
            "Cantidad de items":u_data.shape[0]}


# Devuelve el usuario que acumula más horas jugadas para el género ingresado como parametro y una lista de la 
# acumulación de horas jugadas por año de lanzamiento.
@app.get("/UserForGenre/{genero}")
def UserForGenre(genero : str):
    df_user_gen = pd.read_parquet('Archivos API/def_userforgenre.parquet')

    df_gen = df_user_gen[df_user_gen['genres'].apply(lambda x: genero in x)]
    tot = df_gen.groupby(['user_id']).agg({'playtime': 'sum'}).reset_index()
    u_most = tot.sort_values(by='playtime',ascending=False).iloc[0,0]
    df_user = df_gen[df_gen['user_id']==u_most]
    df_user = df_user.groupby(['release_year']).agg({'playtime': 'sum'}).reset_index()
    
    df_user.rename(columns={'release_year':'Año','playtime':'Horas'},inplace=True)

    res_dict = df_user.to_dict(orient='records')

    return {f"Usuario con más horas jugadas para Genero '{genero}'" : u_most, "Horas jugadas":res_dict}



# Devuelve el top 3 de desarrolladores con juegos MÁS recomendados por usuarios para el año dado. Se analiza basado
# en las variablses recommend = True y sentiment_analysis = 2 (positivo).
@app.get("/best_developer_year/{anio}")
def best_developer_year(anio : int):

    df_best_dev = pd.read_parquet('Archivos API/def_best_dev.parquet')
    df_best = df_best_dev[(df_best_dev['recommend'])&(df_best_dev['sentiment_analysis']==2)&(df_best_dev['release_year']==anio)]

    p1 = df_best['developer'].value_counts().index[0]
    tam = df_best['developer'].value_counts().size
    if  tam > 1:
        p2 = df_best['developer'].value_counts().index[1]
        if tam > 2:
            p3 = df_best['developer'].value_counts().index[2]
        else:
            p3 = None
    else:
        p2 = None
        p3 = None
    
    return [{"Puesto 1":p1,"Puesto 2":p2,"Puesto 3":p3}]


# Devuelve un diccionario con el nombre del desarrollador ingresado por parametro como llave y una lista con la 
# cantidad total de registros de reseñas de usuarios que se encuentren categorizados con un análisis de sentimiento 
# como valor positivo o negativo.
@app.get("/developer_reviews_analysis/{desarrolladora}")
def developer_reviews_analysis(desarrolladora : str):

    df_dev_rev = pd.read_parquet('Archivos API/def_dev_rev.parquet')
    df_dev = df_dev_rev[df_dev_rev['developer']==desarrolladora]

    return {f"{desarrolladora}":{'Negative': {df_dev[df_dev['sentiment_analysis']==0].shape[0]},
                                 'Positive': {df_dev[df_dev['sentiment_analysis']==2].shape[0]}}}

@app.get("/recomendacion_juego/{id_producto}")
def recomendacion_juego (id_producto : int):

    lista_reco = []
    
    return lista_reco

    