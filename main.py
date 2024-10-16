import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from jinja2 import Template
from sklearn.metrics.pairwise import cosine_similarity


#http://127.0.0.1:8000

app = FastAPI()

@app.get("/")
def index():
    return {
        "Mensaje de bienvenida": [
            "Proyecto Individual 1 - Sistema de Recomendacion STEAM",
            "Desarrollado por: Carolina Cardenas"
        ]
    }

# Devuelve la cantidad de items y porcentaje de contenido Free por año para la empresa desarrolladora ingresada como
# parametro.
@app.get("/developer/{desarrollador}")
def developer(desarrollador : str):

    # Se importa el archivo
    df_dev = pd.read_parquet('Archivos API/def_developer.parquet')
         # Columnas:
            # developer
            # item_id
            # release_year
            # price

    if desarrollador in df_dev['developer'].values:
        
        # Se crea un DataFrame que contiene solo los registros para el desarrollador especificado
        dev = df_dev[df_dev['developer']==desarrollador]
        
        # Se crean las columnas 'free' y 'tot' para hacer el conteo de items
        dev['free']=dev['price'].apply(lambda x: 1 if x == 0 else 0) # 1 para cada item Free
        dev['tot']=1

        # Se agrupan los registros por desarrollador y año. Se suma la cantidad de items Free y se cuentan los Total
        dev = dev.groupby(['developer','release_year']).agg({'free': 'sum','tot':'count'}).reset_index()
        
        # Se calcula el porcentaje de contenido Free
        dev['percentage']=((dev['free']/dev['tot'])*100).round(2)
        
        # Se borran las columnas auxiliares y se cambian los nombres de las que contienen el resultado
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
    
    else:

        return f'El desarrollador {desarrollador} no se encuentra en los registros'


# Devuelve la cantidad de dinero gastado por el usuario ingresado como parametro, el porcentaje de recomendación en 
# base a reviews.recommend y cantidad de items.
@app.get("/userdata/{user_id}")
def userdata(user_id : str):

    # Se importa el archivo 
    df_user = pd.read_parquet('Archivos API/def_userdata.parquet')
        # Columnas:
            # user_id
            # item_id
            # recommend
            # price

    if user_id in df_user['user_id'].values:
        
        # Se crea un DataFrame que contiene solo los registros para el usuario especificado
        u_data = df_user[df_user['user_id']==user_id]

        #Se calculan directamente los valores solicitados y se devuelven en el formato solicitado
        return {"User":user_id,"Dinero gastado":float(u_data['price'].sum()),
                "% Recomendacion":(u_data[u_data['recommend']].shape[0]/u_data.shape[0])*100,
                "Cantidad de items":u_data.shape[0]}
    
    else:

        return f'El usuario {user_id} no se encuentra en los registros'


# Devuelve el usuario que acumula más horas jugadas para el género ingresado como parametro y una lista de la 
# acumulación de horas jugadas por año de lanzamiento.
@app.get("/UserForGenre/{genero}")
def UserForGenre(genero : str):

    # Se importa el archivo
    df_user_gen = pd.read_parquet('Archivos API/def_userforgenre.parquet')
        # Columnas:
            # user_id
            # item_id
            # playtime
            # genres
            # release_year

    # Se crea un DataFrame con los registros que contienen en su lista de generos el genero ingresado por parametro
    df_gen = df_user_gen[df_user_gen['genres'].apply(lambda x: genero in x)]
    
    # Se agrupan los registros por usuario y se suman los tiempos de juego
    tot = df_gen.groupby(['user_id']).agg({'playtime': 'sum'}).reset_index()
    
    if tot.size > 0:

        # Se ordenan los tiempos de juego y se toma el usuario correspondiente al mayor valor
        u_most = tot.sort_values(by='playtime',ascending=False).iloc[0,0]

        # Se filtra el DataFrame que contenia solo los registros del genero indicado para el usuario encontrado
        df_user = df_gen[df_gen['user_id']==u_most]

        # Se agrupan los resultados por año
        df_user = df_user.groupby(['release_year']).agg({'playtime': 'sum'}).reset_index()

        # Se renombran las columnas y se crea el diccionario para devolver
        df_user.rename(columns={'release_year':'Año','playtime':'Horas'},inplace=True)
        res_dict = df_user.to_dict(orient='records')

        return {f"Usuario con más horas jugadas para Genero '{genero}'" : u_most, 
                "Horas jugadas":res_dict}
    
    else:

        return f"No hay registros de horas de juego para Genero '{genero}'"



# Devuelve el top 3 de desarrolladores con juegos MÁS recomendados por usuarios para el año dado. Se analiza basado
# en las variablses recommend = True y sentiment_analysis = 2 (positivo).
@app.get("/best_developer_year/{anio}")
def best_developer_year(anio : int):

    # Se importa el archivo
    df_best_dev = pd.read_parquet('Archivos API/def_best_dev.parquet')
        # Columnas:
            # developer
            # item_id
            # release_year
            # recommend
            # sentiment_analysis

    # Se verifica que el año se encuentre en el DataFrame       
    if anio in  df_best_dev['release_year'].values:

        # Se crea un DataFrame con los registros que corresponden al año ingresado por parametro y que son recomendados
        # y tienen un analisis de sentimiento positivo 
        df_best = df_best_dev[(df_best_dev['recommend'])&(df_best_dev['sentiment_analysis']==2)&(df_best_dev['release_year']==anio)]

        # Se ordenan los developer segun su frecuencia en orden descendente y se toman los 3 primeros
        p1 = df_best['developer'].value_counts().index[0]
        tam = df_best['developer'].value_counts().size
        
        # Se verifica que si existan minimo 3 desarrolladoras para poder entregar la respuesta
        if  tam > 1:
            p2 = df_best['developer'].value_counts().index[1]
            if tam > 2:
                p3 = df_best['developer'].value_counts().index[2]
            else:
                p3 = None
        else:
            p2 = None
            p3 = None
        
        return [{"Puesto 1":p1,"Puesto 2":p2,"Puesto 3":p3}] # Se devuelven los datos en el formato solicitado
    
    else:

        return f"No se encontraron juegos lanzados en {anio}"


# Devuelve un diccionario con el nombre del desarrollador ingresado por parametro como llave y una lista con la 
# cantidad total de registros de reseñas de usuarios que se encuentren categorizados con un análisis de sentimiento 
# como valor positivo o negativo.
@app.get("/developer_reviews_analysis/{desarrolladora}")
def developer_reviews_analysis(desarrolladora : str):

    # Sse importa el archivo
    df_dev_rev = pd.read_parquet('Archivos API/def_dev_rev.parquet')
        # Columnas:
            # developer
            # item_id
            # sentiment_analysis

    if desarrolladora in df_dev_rev['developer'].values:

        # Se crea un DataFrame que contiene solo los registros para la desarrolladora especificada
        df_dev = df_dev_rev[df_dev_rev['developer']==desarrolladora]

        #Se calculan directamente los valores solicitados y se devuelven en el formato solicitado
        return {f"{desarrolladora}":{'Negative': {df_dev[df_dev['sentiment_analysis']==0].shape[0]},
                                    'Positive': {df_dev[df_dev['sentiment_analysis']==2].shape[0]}}}

    else:

        return f'El desarrollador {desarrolladora} no se encuentra en los registros'

#  Devuelve una lista con 5 juegos recomendados similares al ingresado por parametro
@app.get("/recomendacion_juego/{id_producto}")
def recomendacion_juego (id_producto : int):

    # Se importa el archivo
    games_feat = pd.read_parquet('Archivos API/def_recom.parquet')
        # Columnas:
            # release_year
            # price
            # todos los valores unicos de genres, tags y specs

    # Se verifica que el juego exista
    if id_producto in games_feat['item_id'].values:
        
        # Se calcula la matriz de similitud del coseno
        matrix = cosine_similarity(games_feat.drop(columns=['item_name','item_id']))

        # Se toma el indice que corresponde al juego ingresado por parametro
        ind = games_feat.index[games_feat['item_id']==id_producto]

        # Se crea una lista con todos los valores de la matriz correspondientes a ese indice y se ordena de manera descendente
        sim = list(enumerate(matrix[ind].flatten()))
        sim = sorted(sim, key=lambda x: x[1], reverse=True)

        # Se toman los indices de los 5 primeros elementos
        recom_ind = [i for i, puntaje in sim[1:6]]

        # Se toman los nombres que corresponden a esos indices
        recom_nom = games_feat['item_name'].iloc[recom_ind].tolist()

        # Se crea un diccionario con los indices y los nombres de los juegos a recomendar
        l = dict(zip(recom_nom, recom_ind))

        # Se toma el nombre del juego ingresado por parametro
        nom = games_feat.iloc[ind,1].values
        
        return f"Juegos recomendados segun {nom} (id {id_producto}): {l}"
    
    else:

        return f"El juego {id_producto} no esta en la base de datos"
    