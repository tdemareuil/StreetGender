# StreetGender

This repository is the output of a week-end project I did in October 2020. Inspired by [this](https://towardsdatascience.com/what-can-analysing-more-than-2-million-street-names-reveal-c94be585759?gi=dd685ebcf5c5) Medium article, I wanted to analyze street names in France, and especially in the city of Paris, to determine what percentage of them correspond to women vs men (TL;DR: not so much). The challenging part of the work was to accurately classify the roads as either masculine or feminine (when they included famous people's names), and the others as neutral - I detail my method and the remaining errors below. I wrapped up the code into a Python module with a single class, `StreetGender`, that you can use to classify the streets from any place in France and to plot a street map coloured by gender - see 'Quick start' and examples below.

<br>

## Repo contents

You'll find here:
- a Python module containing an all-in-one class, `StreetGender`
- the `environment.yml` file required to run the code
- examples of output for the city of Paris (static / png format and interactive / html format)

<br>

## Quick start

For an easy start, you can analyze any place (for now, only in France...!) by first creating a new environment:

```bash
conda env create -f environment.yml -n street-gender
conda activate street-gender
```

And then run the following Python lines:

```python
from StreetGender import StreetGender
your_place = StreetGender('your_place')
your_place.get_genders()
your_place.plot_graph()
```

The place name (str) is passed to `osmnx` to query streets on OpenStreetMap - you can pass a city name, a department or any place name recognized by OSM. Note: just don't choose a whole country or a whole region, computations would be too long.

The `get_genders()` method runs gender classification on all street names and returns a table with road names and corresponding genders (can take a few minutes depending on the number of streets to classify). It can take a `gender` argument (either 'M', 'F' or 'N') to output only the list of either masculine, feminine or neutral streets. 

The `plot_graph()` method draws a coloured map of the streets (static) and can take as optional arguments a list of 3 colors (default: `colors=["silver", "cyan", "fuchsia"]`), the legend localization (default: `legend_loc='lower left'`) and a `save`option (bool) to save your map as a PNG file in the current folder. To plot an interactive `folium` map, use the `plot_folium()` method, which can also take `color` and `save` arguments (the latter saves your map as an interactive HTML file). See examples below (static) and in the `examples` folder (interactive).

Other attributes of the class include: `.road_graph` to access the road `networkx` graph object, `.road_table` for the table of road names, and `.gender_table` for the dictionary used during classification.

<br>

## Methodology

Determining the gender of a street names isn't an easy task. It's not about determining the gender of words in the street name - this would classify as masculine or feminine names that are just neutral ('Place des Vosges', etc.). To classify only the names that correspond to people, the most straightforward thing to do is use the gender of first names. But when there is no first name, only the last name, how can we know? 'Rue Cassette' or 'Rue de Berry' could very well correspond to a man, a woman, or even none of them (a place for example). To try and solve this problem, I implemented the classification steps below:

1) Use a list of all French first names + associated gender in order to classify the roads that include a first name. I used the list of all first names between 1900 and 2019 published by INSEE at this [address](https://www.insee.fr/fr/statistiques/2540004?sommaire=4767262#consulter).

2) Do the same with first names from other languages: I added English first names, extracted from the list of all first names given in Scotland since 1910 (available [here](https://www.nrscotland.gov.uk/files//statistics/babies-names/19/babies-first-names-all-names-all-years.csv)) and some of the most common Italian first names (found [here](https://www.rinonline.it/studenti_nomi_propri_persona.htm)).

3) To classify some of the roads without a first name, hard-code the gender of a list of words commonly included in street names - especially the military titles, religious titles or titles of nobility (ex: 'Maréchal', 'Général', 'Président', 'Madame', 'Monsieur', 'Duc', 'Duchesse', etc.).

4) To classify the remaining roads named after a famous person but not including their first name or title (ex: 'Rue Monge', 'Rue La Boétie', 'Avenue de Mortemart'), use the `wikipedia` package to search for the current word (ex: 'Monge') on Wikipedia. The code reads the top 3 results, and stops if it finds a first name - in this case, it's highly likely that the road name corresponds to a person, and we can classify their gender. Example: `wikipedia.search('lagrange')` outputs `['Joseph-Louis Lagrange', 'Lagrange multiplier', 'Lagrange (disambiguation)']`, in which 'Joesph' is identified as a man.

<br>

Misclassifications can happen for several reasons:

* When the first name isn't recognized - i.e. uncommon names in French, English and Italian that I don't have in my list of first names, for example Spanish or Deutsch first names.

* When the road name is mistakingly interpreted as a person, because it exists in the list of first names. Example: 'Rue Blanche' where Blanche is a color but can also be a first name, 'Rue des Iris' where Iris is a flower, or 'Place de Lorraine' where Lorraine is a region. In most case, once spotted we can remove the misleading first name from the list. Note that I already removed the first names that were given to less than 100 people since 1900, as rare names such as 'Odessa' or 'Annecy' (names of cities) created errors.

* When the first person that appears on Wikipedia based on the road name isn't the one after which the road was named - for example 'Jenner' outputs 'Kylie Jenner' before 'Edward Jenner' (English physician), and 'Bosquet' outputs 'Céline Bosquet' (TV host) before 'Maréchal Bosquet' (French military officer). A workaround would be to eliminate profiles whose birth date is too recent (as contemporary people often do not give their names to roads), but this would require additional wikipedia scraping. Unfortunately, the Python API for Wikipedia doesn't offer an option to customly sort search results (the results order is based on 'relevance', which is unclear and can vary even when we send the same query several times).

<br>

## Analysis & Next steps

This was a short project, and as seen above classifying the gender of street names can become quite complex, so my method is still far from perfect. However, it clearly confirms that women are (immensely) under-represented in street names... It's true that a majority of historical, politcal or military figures, which often end up on street names, are men - but still, under-representation is blatant. Even with the current efforts to rename streets or name new streets after famous women, we're not there yet...!

The next steps in terms of code would be to:
* decrease the number of classification mistakes (maybe with deeper Wikipedia scraping - but this would increase computing time)
* decrease the number of streets that swim through the mesh of the net and remain unclassified (neutral), while they do correspond to people (e.g. by adding first names from other languages in the gender dictionary)
* adapt the code and method to other languages

In terms of analysis, there are many possibilities:
* compare the major French cities (Paris, Lyon, Marseille, etc.) to see which one has the less sexist street names
* produce a heatmap of French departments, showing which ones have the less sexist street names, to see if there is a geographical difference
* produce more statistics about street names: what's the percentage of religious-based street names, etc.
* use wikipedia scraping to learn more about street names: from which century or historical period does the majority of names come from? Which job / occupation is the most represented? Who are these few women on street names?? - Lots of interesting stuff to discover!

<br>

## Examples

![Paris PNG](examples/paris_gendered_street_map.png)

<img align="center" src="examples/chatou_gendered_street_map.png" width="678" alt="Chatou PNG">

<br>

![Haute-Savoie PNG](examples/haute-savoie_gendered_street_map.png)

