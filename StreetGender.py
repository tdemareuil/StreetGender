import pandas as pd
from unidecode import unidecode
import osmnx as ox
ox.config(use_cache=True, log_console=True)
from osmnx import utils_graph
import re
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
from tqdm import tqdm
import wikipedia
wikipedia.set_rate_limiting(True)
wikipedia.API_URL = 'https://en.wikipedia.org/w/api.php'
from itertools import chain
import json
import folium
import time


class StreetGender:
    
    def __init__(self, place: str, network_type='drive'): # 'walk', 'bike', 'drive', 'all' or 'all_private'
        
        # download and clean INSEE's list of first names
        genders = pd.read_csv('https://www.insee.fr/fr/statistiques/fichier/2540004/nat2019_csv.zip', sep=";")[['preusuel','sexe', 'nombre']]
        genders['preusuel'] = genders['preusuel'].apply(lambda x: unidecode(str.lower(str(x))))
        genders = genders.sort_values('nombre').drop_duplicates('preusuel', keep='last')
        genders = genders[genders['nombre']>=100]
        genders = genders[genders['preusuel']!='camille'] # remove Camille (2) as most street Camilles are men (1)
        genders = genders[genders['preusuel']!='blanche']
        genders = genders.reset_index(drop=True).drop(columns=['nombre'])
        
        # add English first names
        genders_en = pd.read_csv('https://www.nrscotland.gov.uk/files//statistics/babies-names/19/babies-first-names-all-names-all-years.csv')[['sex','FirstForename','number']]
        genders_en = genders_en[genders_en['number']>=20]
        genders_en['preusuel'] = genders_en['FirstForename'].apply(lambda x: unidecode(str.lower(str(x))))
        genders_en = genders_en.drop_duplicates('preusuel')
        genders_en['sexe'] = genders_en['sex'].apply(lambda x: 1 if x=='B' else 2)
        genders_en = genders_en.reset_index(drop=True).drop(columns=['FirstForename','number','sex'])

        # add Italian first names
        ragazzo = re.split(', |[.\n ]', ragazzo)
		ragazzo = [x for x in ragazzo if len(x)>0]
		ragazza = re.split(', |[.\n ]', ragazza)
		ragazza = [x for x in ragazza if len(x)>0]
		genders_it = {} 
		for x in ragazzo:
		    genders_it[x] = 1
		for x in ragazza:
		    genders_it[x] = 2
		genders_it = pd.DataFrame.from_dict(genders_it, orient='index')
		genders_it = genders_it.reset_index()
		genders_it.columns = ['preusuel','sexe']

        # complement the gender table
        more_names = pd.DataFrame.from_dict(custom_dict, orient='index')
        more_names = more_names.reset_index()
        more_names.columns = ['preusuel','sexe']
        genders = pd.concat([genders, more_names, genders_en, genders_it], axis=0)
        genders['preusuel'] = genders['preusuel'].apply(lambda x: unidecode(str.lower(str(x))))
        genders = genders.drop_duplicates('preusuel')
        mistakes = ['france', 'alma', 'barbe', 'lilas', 'milan', 'brune', 'felicite',
                    'nancy', 'grace', 'lorraine', 'evy', 'loup', 'iris',
                    'colombe', 'jan', 'harmonie', 'julienne', 'abbey', 'andrea', 'kim',
                    'brittany', 'river', 'line', 'lou', 'tracy', 'yvette', 'sonia',
                    'india', 'leah', 'pamela', 'stacey', 'eliza', 'athena', 'prince',
                    'violet', 'desiree', 'vivienne', 'charlie']
        genders = genders[~genders['preusuel'].isin(mistakes)]
        genders =  genders.reset_index(drop=True)

        self.gender_table = genders
        self.place = place
        self.network_type = network_type
        self._road_graph = None
        self._road_table = None
        self._road_genders = None
        print('Class instance initiated.')
       
    @property
    def road_graph(self):
        if self._road_graph is not None:
            return self._road_graph
        else:
            print('Querying road graph from OSM...')
            G = ox.graph_from_place(self.place, network_type=self.network_type)
            G = ox.get_undirected(G)
            self._road_graph = G
        print('Road graph successfully fetched.')
        return self._road_graph
    
    
    @property
    def road_table(self):
        if self._road_table is not None:
            return self._road_table
        else:
            if self._road_graph is not None:
                G = self._road_graph
            else:
                G = self.road_graph
            roads = ox.graph_to_gdfs(G, nodes=False)[['name']]
            self._road_table = roads
            return self._road_table


    def _classify_gender(self, name: list):
        # set gender to neutral
        g = None

        # iterate through elements of the road name to try classifying
        for el in name:
            try:
                g = int(self.gender_table[self.gender_table['preusuel']==el]['sexe'])
                break
            except:
                continue

        # for the names that remained neutral, search wikipedia
        if (g == None and len(name)==2) or \
           (g == None and len(name)>3 and name[2] in ['de','d', 'du']): # case of 'Rue XX' or 'Rue XX de XX'
            wikipedia.set_lang('en')
            time.sleep(0.01)
            results = wikipedia.search(name[1])[:3]
            results = [re.split(" |\-|\'", k) for k in results]
            results = list(chain.from_iterable(results))
            for k in results:
                k = unidecode(str.lower(str(k)))
                try:
                    g = int(self.gender_table[self.gender_table['preusuel']==k]['sexe'])
                    break
                except:
                    continue
            if g == None: # if name is still unclassified, search French wikipedia 
                wikipedia.set_lang('fr')
                results = wikipedia.search(name[1])[:3]
                results = [re.split(" |\-|\'", k) for k in results]
                results = list(chain.from_iterable(results))
                for k in results:
                    k = unidecode(str.lower(str(k)))
                    try:
                        g = int(self.gender_table[self.gender_table['preusuel']==k]['sexe'])
                        break
                    except:
                        continue

        elif g == None and len(name)==3 and name[1] in ['le','la', 'de', 'd']: # case of 'Rue de XX'
            wikipedia.set_lang('en')
            time.sleep(0.01)
            results = wikipedia.search(name[2])[:3]
            results = [re.split(" |\-|\'", k) for k in results]
            results = list(chain.from_iterable(results))
            for k in results:
                k = unidecode(str.lower(str(k)))
                try:
                    g = int(self.gender_table[self.gender_table['preusuel']==k]['sexe'])
                    break
                except:
                    continue
            if g == None: # if name is still unclassified, search French wikipedia 
                wikipedia.set_lang('fr')
                results = wikipedia.search(name[2])[:3]
                results = [re.split(" |\-|\'", k) for k in results]
                results = list(chain.from_iterable(results))
                for k in results:
                    k = unidecode(str.lower(str(k)))
                    try:
                        g = int(self.gender_table[self.gender_table['preusuel']==k]['sexe'])
                        break
                    except:
                        continue
        
        if g == None: # for the names still unclassified, assign 0 (neutral)
            g = 0

        return g

    
    def get_genders(self, gender=None):
        tqdm.pandas()
        if self._road_genders is not None:
            roads = self._road_genders
            if gender == None:
                return self._road_genders
            else:
                if gender == 'M':
                    return self.masculine
                elif gender == 'F':
                    return self.feminine
                elif gender == 'N':
                    return self.neutral
                else:
                    raise ValueError("Please pass 'M', 'F' or 'N' as gender argument.")
                
        else:
            if self._road_table is not None:
                roads = self._road_table
            else:
                roads = self.road_table
            print('Classifying streets...')

            # create intermediate table with no duplicates to compute genders
            roads['name_lower'] = roads['name'].apply(lambda x: unidecode(str.lower(str(x))))
            intermediate = pd.DataFrame(roads['name_lower'].drop_duplicates())
            intermediate['name_preprocessed'] = intermediate['name_lower'].apply(lambda x: re.split(" |\-|\'", x))
            intermediate['gender'] = intermediate['name_preprocessed'].progress_apply(lambda x: self._classify_gender(name=x))

            # merge back with roads table
            roads = roads.merge(intermediate, on='name_lower')
            self._road_genders = roads
            
            # store masc, fem and neutral streets in separate attributes
            masc = list(roads[roads['gender']==1]['name'])
            self.masculine = list(set([x for x in masc if type(x) == str])) # remove duplicated and list items
            fem = list(roads[roads['gender']==2]['name'])
            self.feminine = list(set([x for x in fem if type(x) == str]))
            neut = list(roads[roads['gender']==0]['name'])
            self.neutral = list(set([x for x in neut if type(x) == str]))
            
            if gender == None:
                print('Street genders successfuly computed.')
                return self._road_genders
            else:
                if gender == 'M':
                    return self.masculine
                elif gender == 'F':
                    return self.feminine
                elif gender == 'N':
                    return self.neutral
                else:
                    raise ValueError("Please pass 'M', 'F' or 'N' as gender argument.")
    
    
    def plot_graph(self, colors=["silver", "cyan", "fuchsia"], legend_loc='lower left', save=False):
        if self._road_genders is not None:
            roads = self._road_genders
        else:
            roads = self.get_genders()

        # add gender attribute to the road graph
        # for that, we first add the gender column from `roads` to the full road geodataframe (`edges`),
        # thanks to a common sorting order based on the ['name_lower'] column.
        G = self._road_graph
        edges = ox.graph_to_gdfs(G, nodes=False)
        roads = roads.sort_values('name_lower', ignore_index=True) # sort `roads` on name_lower
        edges['name_lower'] = edges['name'].apply(lambda x: unidecode(str.lower(str(x)))) 
        edges = edges.sort_values('name_lower', ignore_index=True) # sort `edges` on name_lower
        edges['gender'] = roads['gender'] # add gender column from `roads` to `edges` - everything should match!
        for index, row in edges.iterrows():
            G.edges[row['u'], row['v'], row['key']]['gender'] = row['gender']

        # choose colors
        gender_colors = LinearSegmentedColormap.from_list("mycmap", colors)
        ec = ox.plot.get_edge_colors_by_attr(G, 'gender', cmap=gender_colors)

        # plot graph
        fig, ax = ox.plot_graph(G, edge_color=ec, bgcolor='white', node_size=0, figsize=(18, 18), show=False)

        # plot legend
        edges['name'] = edges['name'].apply(lambda x: '' if type(x)!=str else x)
        edges = edges.drop_duplicates('name')
        frequencies = round(edges['gender'].value_counts(normalize=True) * 100, 1)
        freq_neut = frequencies[0]
        try:
            freq_masc = frequencies[1]
        except:
            freq_masc = 0
        try: 
            freq_fem = frequencies[2]
        except:
            freq_fem = 0
        plt.rcParams["font.family"] = "monospace"
        custom_lines = [Line2D([0], [0], color='cyan', lw=3),
                        Line2D([0], [0], color='fuchsia', lw=3),
                        Line2D([0], [0], color='silver', lw=3)]
        l = ax.legend(custom_lines, 
                  [f"Nom d'homme: {freq_masc}%", f"Nom de femme: {freq_fem}%", f"Neutre: {freq_neut}%"],
                  title=f"Rues de {self.place}\nclassées par sexe\n",
                  loc=legend_loc, frameon=False, fontsize='large')
        plt.setp(l.get_title(), multialignment='center', family='monospace', weight='black', size=22)
        plt.show();
        
        # save as png
        if save:
            fig.set_frameon(True)
            fig.savefig(f'{str.lower(self.place)}_gendered_street_map.png', 
                        facecolor=fig.get_facecolor(), bbox_inches='tight')
            print(f'Map successfully saved as {str.lower(self.place)}_gendered_street_map.png')

    
    def plot_folium(self, colors=["silver", "cyan", "fuchsia"], save=False):
        if self._road_genders is not None:
            roads = self._road_genders
        else:
            roads = self.get_genders()

        # add gender attribute to the road graph
        # for that, we first add the gender column from `roads` to the full road geodataframe (`edges`),
        # thanks to a common sorting order based on the ['name_lower'] column.
        G = self._road_graph
        edges = ox.graph_to_gdfs(G, nodes=False)
        roads = roads.sort_values('name_lower', ignore_index=True) # sort `roads` on name_lower
        edges['name_lower'] = edges['name'].apply(lambda x: unidecode(str.lower(str(x)))) 
        edges = edges.sort_values('name_lower', ignore_index=True) # sort `edges` on name_lower
        edges['gender'] = roads['gender'] # add gender column from `roads` to `edges` - everything should match!
        for index, row in edges.iterrows():
            G.edges[row['u'], row['v'], row['key']]['gender'] = row['gender']

        # add color attribute to the road graph
        edges = ox.graph_to_gdfs(G, nodes=False)
        for index, row in edges.iterrows():
            if row['gender'] == 1:
                c = colors[1]
            elif row['gender'] == 2:
                c = colors[2]
            else:
                c = colors[0]
            G.edges[row['u'], row['v'], row['key']]['edge_color'] = c

        # plot the street network with folium and save as html if required
        m = self._plot_graph_folium(G, popup_attribute='name', edge_width=2, tiles='cartodbpositron')
        if save:
            m.save(f'{str.lower(self.place)}_gendered_street_map.html')
            print(f'Map successfully saved as {str.lower(self.place)}_gendered_street_map.html')
        return m

    
    @staticmethod
    def _plot_graph_folium(G, graph_map=None, popup_attribute=None,
                           tiles="cartodbpositron", zoom=1, fit_bounds=True,
                           edge_width=5, edge_opacity=1, **kwargs):
        """
        Plot a networkx.MultiDiGraph on an interactive folium web map.
        Note that anything larger than a small city can take a long time to plot
        and create a large web map file that is very slow to load as JavaScript.
        """
        
        # create gdf of the graph edges
        gdf_edges = utils_graph.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)

        # get graph centroid
        x, y = gdf_edges.unary_union.centroid.xy
        graph_centroid = (y[0], x[0])

        # create a new folium web map if one wasn't passed in through the graph_map argument
        if graph_map is None:
            graph_map = folium.Map(location=graph_centroid, zoom_start=zoom, tiles=tiles)

        # add each graph edge to the map (including custom width, color and popups)
        for _, row in gdf_edges.iterrows():
            pl = ox.folium._make_folium_polyline(
                edge=row,
                edge_color=row['edge_color'],
                edge_width=edge_width,
                edge_opacity=edge_opacity,
                popup_attribute=popup_attribute,
                **kwargs,
            )
            pl.add_to(graph_map)

        # if fit_bounds is True, fit the map to the bounds of the route by passing
        # list of lat-lng points as [southwest, northeast]
        if fit_bounds and isinstance(graph_map, folium.Map):
            tb = gdf_edges.total_bounds
            bounds = [[tb[1], tb[0]], [tb[3], tb[2]]]
            graph_map.fit_bounds(bounds)

        return graph_map


custom_dict = {
            # titles
            'Maréchal':1, 'Maréchaux':1, 'Général':1, 'Capitaine':1, 'Commandant':1, 'Adjudant':1,
            'Colonel':1, 'Colonels':1, 'Amiral':1, 'Amiraux':1, 'Caporal':1, 'Sergent':1, 'Brigadier':1,
            'Soldat':1, 'Lieutenant':1, 'Major':1, 'Commandeur':1, 'combattants':1,

            'Saint':1, 'Saints':1, 'Sainte':2, 'Saintes':2, 'Révérend':1, 'Mère':2, 'Père':1, 'Pères':1, 
            'Bienheureux':1, 'Bienheureuse':2, 'Bienheureuses':2, 'Chanoine':1, 'Cardinal':1, 'Evêque':1, 
            'Evêques':1, 'Archevêque':1, 'Abbé':1, 'Abbesse':2, 'Vicaire':1, 'Papes':1, 'chretien':1,
            'Dieu':1, 'Dieux':1, 'Déesse':2, 'Déesses':2, 'Capucins':1, 'Capucines':2, 'Moine':1, 'Madone':1,
            'Moines':1, 'Moniales':2, 'Curé':1, 'Pasteur':1, 'ermite':1, 'franciscains':1, 'minimes':1,
            'franciscaines':2, 'dominicains':1, 'dominicaines':2, 'abbesses':2, 'clerc':1, 'clercs':1,
            'Mères':2, 'Cordelières':2, 'vierge':2, 'vierges':2, 'patriarche':1, 'patriarches':1, 
            'ursulines':1, 'prêtre':1, 'prêtres':1, 'recteur':1,

            'Duc':1, 'Ducs':1, 'Duchesse':2, 'Duchesses':2, 'Comte':1, 'Comtes':1, 'Comtesse':2, 
            'Comtesses':2, 'Vicomte':1, 'Vicomtesse':2, 'Baron':1, 'Barons':1, 'Baronne':2, 'Baronnes':2, 
            'Princesse':2, 'Prince':2, 'princes':1, 'princesses':2, 'Roi':1, 'Rois':1, 'Reine':2, 'Reines':2, 
            'Marquise':2, 'Marquis':1, 'Lord':1, 'Lady':2, 'Dauphin':1, 'Dauphine':1, 'Chevalier':1, 
            'Chevaliers':1, 'Infante':2, 'Empereur':1, 'Emperesse':2, 'Régent':1, 'Régente':2, 'Archiduc':1, 
            'Chatelain':1, 'Chatelaine':2, 'Chapelaines':2, 'Bourgeois':1, 'Bourgeoise':2, 'Bourgeoises':2,
            'favorite':2, 'favorites':2, 

            'Président':1, 'Présidente':2, 'Consul':1, 'Maire':1, 'Ambassadeur':1, 'Ambassadeurs':1,
            'Ambassadrice':2, 'Ambassadrices':2, 'Directeur':1, 'Directrice':2, 'Docteur':1, 'Inspecteur':1,
            'Professeur':1, 'Maître':1, 'Maîtresse':2, 'Joueur':1, 'Joueurs':1, 'Joueuse':2, 'Joueuses':2,
            'Fille':2, 'Filles':2, 'Fils':1, 'Soeur':2, 'Soeurs':2, 'Frère':1, 'Frères':1, 'cadet':1,
            'Docteurs':1, 'Cousins':1, 'Cousin':1, 'Cousine':2, 'Cousines':2, 'douanier':1, 'douniers':1,
            'cheminots':1, 'dechargeurs':1, 'Banquier':1, 'agent':1, 'bergers':1, 'garçon':1, 'garçons':1,
            'maraichers':1, 'conseiller':1, 'fillettes':2, 'jardiniers':1, 'arquebusiers':1, 'chasseurs':1,
            'poissoniers':1, 'poissonnières':1,

            'Mademoiselle':2, 'Demoiselle':2, 'Demoiselles':2, 'Dame':2, 'Dames':2, 'Messieurs':1, 'Mesdames':2,
            'Monseigneur':1, 'Seigneur':1, 'Seigneurs':1, 'Messire':1, 'Madame':2, 'Monsieur':1,

            # mistakes
            'Vinci':1, 'Gogh':1, 'Rembrandt':1, 'Gandhi':1, 'Sisley':1, 'Loo':1, 'Péguy':1, 'Turgot':1,
            'Pleyel':1, 'Jenner':1, 'Chanez':1, 'Auber':1, 'Pradier':1, 'Huysmans':1, 'Barrault':1,
            'Richer':1, 'Boutin':1, 'Fortuny':1, 'Bouchardon':1, 'Valadon':1, 'Payenne':1, 'Brey':1,
            'Godefroy':1, 'Tagore':1, 'Berthollet':1, 'Nobel':1, 'Viollet':1, 'Vavin':1, 'Rossini':1,
            'Castille':2, 'Brun':1, 'Boétie':1, 'Evariste':1, 'Godefroy':1, 'Valois':1, 'Goncourt':1,
            'Tchaikovsky':1, 'Nicolai':1, 'Paganini':1, 'Bernoulli':1, 'Alembert':1, 'Marx':1, 'Franklin':1,
            'Reynaldo':1, 'Berri':1, 'Bruyere':1, 'Lesseps':1, 'Fenelon':1, 'Mareuil':1, 'nan':0,
            'Dupont':1, 'Malmaisons':2, 'Malmaison':2, 'Valois':1, 'Blaise':1, 'Bougainville':1, 'Louvois':1,
            'Colbert':1, 'Faustin':1, 'Chavez':1, 'Mozart':1, 'Desprez':1, 'Froidevaux':1, 'Chapon':1,
            'Gluck':1, 'Berthier':1, 'Grimaud':1, 'Chapon':1, 'Bouvier':1, 'Gauthey':1, 'Dyck':1, 'Monceau':0,
            'Royal':0, 'Favart':1, 'Rauch':1, 'Jonquoy':1, 'Gerando':1, 'Bruller':1, 'Cepre':1, 'Pinel':1,
            'Laferrière':1, 'Gaetano':1, 'Lentonnet':1, 'Mignot':1, 'Mayet':1, 'Pasquier':1, 'Taylor':1,
            'Dubois':1, 'Brunel':1, 'Hebert':1, 'Lagrange':1, 'Junot':1, 'Dieulafoy':1, 'Houdart':1,
            'Franz':1, 'Mouraud':1, 'Andrieux':1, 'Valette':1, 'Joubert':1, 'Ferrus':1, 'Portefoin':1,
            'Hoche':1, 'Fourneyron':1, 'Lemercier':1, 'Polonceau':1, 'Sibour':1, 'Petrarque':1, 'Bourgoin':1,
            'Thouin':1, 'Benard':1, 'Guénégaud':1, 'Tracy':1, 'Calmels':1, 'Geoffroi':1, 'Villiot':1,
            'Greffulhe':1, 'Tarbé':1, 'Daunay':1, 'Larribe':1, 'Riboutté':1, 'Johannes':1, 'Iannis':1,
            'Guglielmo':1, 'Guillermo':1, 'jan':1, 'buzenval':1, 'dario':1, 'angelo':1, 'giacomo':1,
            'giuseppe':1, 'giovanni':1, 'compoint':1, 'wattignies':0, 'cavé':1, 'Castiglione':0, 'dom':1, 
            'girodet':1, 'presles':1, 'chartres':0, 'julienne':1, 'marois':1, 'cahors':0, 'riberolle':1,
            'moreau':1, 'vezelay':0, 'amiens':0, 'fourviere':0, 'rouen':0, 'bazeilles':0, 'Pecquay':1,
            'duras':1, 'cardinale':1, 'aubry':1, 'petel':1, 'vineuse':0, 'dufrenoy':1, 'lagarde':1,
            'paradis':0, 'clery':0, 'deshayes':1, 'keller':1, 'fabre':1, 'narbonne':0, 'boyer':1, 'ponthieu':0,
            'parme':0, 'halle':0, 'peclet':1, 'Camille':1, 'meaux':0, 'tourville':1, 'salvador':1, 'burq':1,
            'caillou':1, 'napoleon':1, 'Bourbon':1, 'Habsbourg':1, 'croix':0, 'Prairy':0, 'Tahan':1,
            'beauharnais':2, 'Angouleme':1, 'remusat':1, 'bruneseau':1, 'eble':1, 'marinoni':1, 'blanche':0, 
            'evette':1, 'caillaux':1, 'alasseur':1, 'peletier':1, 'hanovre':0, 'bolivie':0, 'chablis':0, 
            'pean':1, 'parme':0, 'bachelet':1, 'darcy':1, 'poitou':0, 'scheffer':1, 'dussoubs':1, 'ramponeau':1,
            'edimbourg':0, 'boutron':1, 'popincourt':1, 'vivienne':1, 'brissac':1, 'buci':1, 'bellart':1, 
            'castellane':1, 'riverin':1, 'verneuil':1, 'poulet':1, 'moufle':1, 'anjou':0, 'nicolet':1,
            'clignancourt':0, 'piat':1, 'tourtille':1, 'mornay':1, 'cardinet':1, 'mercoeur':1, 'saxe':1,
            'lacaze':1, 'girardon':1, 'morand':1, 'bourgon':1, 'sivel':1, 'cauchois':1, 'Diaghilev':1,
            'lheureux':1, 'anvers':0, 'serret':1, 'crimee':0, 'artois':1, 'anjou':1, 'alexandrie':0, 'thiere':1,
            'frochot':1, 'alibert':1, 'talma':1, 'clisson':1, 'lauzin':1, 'chanaleilles':1, 'vignon':1,
            'quincampoix':1, 'bullourde':1, 'desgrais':1, 'boutarel':1, 'marcadet':0, 'beauvau':0, 'lappe':1,
            'drevet':1, 'planchat':1, 'bardinet':1, 'edmund':1, 'crimee':0, 'pigalle':1, 'gazan':1,
            'Erckmann':1, 'voltaire':1, 'brillat':1, 'lautrec':1, 'montequieu':1, 'lassus':1, 'renaudot':1,
            'visitation':2, 'winston':1, 'bayard':1, 'stendhal':1, 'godot':1, 'reims':0, 'vercingetorix':1,
            'maubeuge':0, 'strasbourg':0, 'constantinople':0, 'vaucouleurs':0, 'jasmin':1, 'armaille':1,
            'danville':1, 'laborde':1, 'vineuse':0, 'belhomme':1, 'cheroy':1, 'picot':1, 'valmy':0,
            'lobau':1, 'thoreton':1, 'blanchard':1, 'conti':1, 'titon':1, 'duranti':1, 'mirbel':1,
            'nungesser':1, 'sully':1, 'boucry':1, 'sigmund':1, 'feuillantines':2, 'carnot':1, 'baigneur':1,
            'chasseloup':1, 'carducci':1, 'lally':1, 'gerbert':1, 'montfaucon':1, 'constantin':1, 'casals':1,
            'euryale':1, 'cyrano':1, 'archimede':1, 'montesquieu':1, 'borda':1, 'leroy':1, 'taitbout':1,
            'alleray':1, 'alberic':1, 'ricaut':1, 'rosenwald':1, 'arturo':1, 'denfert':1, 'anselme':1, 
            'bertie':2, 'salomon':1, 'sibelle':2, 'hermann':1, 'Wilhem':1, 'estienne':1, 'crespin':1,
            'sauffroy':1, 'trudaine':1, 'robineau':1, 'griset':1, 'chantilly':0, 'astorg':1, 'compiegne':0,
            'Schutzenberger':1, 'jadin':1, 'seveste':1, 'vey':1, 'villaret':1, 'euler':1, 'vasco':1,
            'markos':1, 'vernier':1, 'thorigny':1, 'theodule':1, 'arnault':1, 'Mstislav':1, 'rousseau':1,
            'gerda':2, 'Rochefoucauld':1, 'spontini':1, 'bessie':2, 'nicolo':1, 'galilee':1, 'mac':1,
            'Wilhelm':1, 'richemont':1, 'coluche':1, 'dode':1, 'berbet':1, 'labois':1, 'franquet':1,
            'Elisée':1, 'myron':1, 'camulogene':1, 'furtado':2, 'charlemagne':1, 'franc':1, 'gall':2, 
            'jay':2, 'bellay':1, 'chauvin':1, 'antonini':1, 'dante':1, 'alberto':1, 'jacopo':1, 'rapee':1,
            'bruxelles':0,
            }

# Italian first names
url = 'https://www.rinonline.it/studenti_nomi_propri_persona.htm'
masc = """Agostino, Alberto, Alessandro, Alessio, Alfio, Alfonso, Amedeo, Angelo, Antonio, Aurelio. 
        Baldassarre, Baldo, Bastiano, Bartolo, Bartolomeo, Benito,  Bernardo, Biagio, Boris, Bruno.
        Calogero, Carlo, Carmelo,  Casimiro, Cesare, Cirillo, Ciro,  Claudio, Corrado, Cosimo.
        Daniele, Danilo, Dante, Dario, Davide, Diego, Dino, Dionisio, Domenico, Duccio.
        Egidio, Elio, Eliseo, Emanuele, Emiliano, Emilio, Ennio,  Enrico, Enzo, Ezio.
        Fabiano, Fabio, Fabrizio, Fausto, Fedele, Felice, Filippo, Flavio, Fortunato, Francesco.
        Gabriele, Gaetano, Gaspare, Gennaro, Gerlando, Giacomo, Giancarlo, Giovanni, Giulio, Giuseppe.
        Iacopo, Ignazio, Igor, Isacco, Isaia, Iside, Isidoro, Italo, Ivano, Ivo.
        Leandro, Leo, Lino, Livio, Lorenzo, Loris, Luca, Luciano, Lucio, Luigi.
        Manuele, Marcello, Marco, Mario, Martino, Massimo, Matteo, Mattia, Michele, Mirco.
        Narciso, Natale, Nazario, Nazzareno, Nestore, Nico, Nicola, Nino, Noè, Nunzio.
        Oliviero, Omar , Omero, Onofrio, Orazio, Orlando, Oscar,  Osvaldo, Otello, Ottavio.
        Paolo, Pasquale, Patrizio, Paride, Pierluigi, Piero, Pietro, Pio, Pippo, Prisco.
        Raffaele, Raimondo, Renato, Renzo, Riccardo, Rino, Roberto, Rocco, Romolo, Ruggero.
        Salvatore, Salvo, Samuele, Sandro, Saverio, Savino, Sebastiano, Sergio, Silvio, Stefano.
        Taddeo, Tancredi, Tarso, Teodoro, Teogene, Tiberio, Tito, Tiziano, Tobia, Tullio,
        Ubaldo, Uberto, Ugo, Ulisse, Ulrico, Ultimo, Umberto, Uranio, Urbano, Ursino.
        Valter , Vasco, Valentino, Valerio, Velio, Viliberto, Vincenzo, Virgilio, Virone, Vittorio,
        Zabedeo, Zaccaria, Zaccheo, Zanobi, Zefiro, Zeno, Zenobio, Zenone, Zetico, Zoilo"""

ragazza = """Angela, Ada, Adelaide, Anna, Antonella, Anita, Alice, Amelia, Anna, Agnese, Alessandra, Alessia,
        Aurora, Angelica,
        Barbara, Betty, Beatrice,
        Calogera, Claudia, Carlotta, Carmen, Carola, Caterina, Cinzia, Clara, Clarissa, Clelia, Concetta,
        Corinna, Cristina,
        Daniela, Dina, Domenica, Debora, Denise, Danila, Dorotea,
        Emanuela, Emilia, Evelyn, Erica, Elena, Elisa, Eva,
        Fiorella, Francesca, Federica, Fabiola, Flavia, Floriana,
        Giovannna, Gabriella, Gerlanda, Giulia, Giuseppina, Giorgia, Gaia, Gemma, Greta,
        Ida, Iole, Iolanda, Irene, Isabella, Iside,
        katia, Ketty,
        Luciana, Laura, Lorena, Loredana, Lucia, Lea, Letizia, Lia, Linda, Luisa,
        Maria, Marcella, Martina, Marzia, Mara, Marisa, Marta, Mirella, Miriam,
        Noemi, Nada,
        Ornella,
        Patrizia, Paola, Piera, Pamela, Piera,
        Roberta, Regina, Raffaella, Rosella,
        Salvatrice, Silvia, Sofia, Sabrina, Sara, Serena, Silvana, Simona, Stefania, Susanna,
        Tiziana, Tea, Teresa,
        Valentina, Valeria"""

