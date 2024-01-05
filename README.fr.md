# Intégration Prix Carburant pour Home-Assistant

Récupération du prix des carburant selon les données de l'[API gouvernementale](https://data.economie.gouv.fr/explore/dataset/prix-des-carburants-en-france-flux-instantane-v2/table/).

Récupère les stations à x kilomètres de votre domicile (ou via une liste définie si utilisation de `configuration.yaml`).
Rafraîchissement des données toutes les heures, il est possible de lancer un rafraîchissement manuel via l'entité `button`.
Un service est mis à disposition pour trouver le meilleur prix d'un carburant donné autour de soi ou de n'importe quelle entité possédant une localisation (`device_tracker`, `person`, `sensor`...).

## Installation

### HACS

HACS > Integrations > Explorer et télécharger des dépôts > Prix Carburant > Télécharger

### Manuelle

Copier le dossier `prix_carburant` dans le dossier `config/custom_components` de votre Home-Assistant.

## Configuration

### via l'interface

Ajoutez une nouvelle intégration, recherchez `Prix Carburant` et remplissez les champs demandés.

### via configuration.yml

Récupérer l'ID des stations voulues sur <https://www.prix-carburants.gouv.fr/>. Pour cela chercher la station, cliquer sur le logo station sur la carte, passer le curseur sur `Voir plan` et noter le numéro qui apparait en bas de votre navigateur. Exemple avec Firefox :

![Récupération d'ID avec Firefox](readme_firefoxid.png)

Puis dans le fichier configuration.yaml, mettre par exemple :

```yaml
sensor:
  platform: prix_carburant
  stations:
    - 59000009
    - 59000080
```

### Exemple de données extraites

`Station Carrefour Market La Poterie E10` - `sensor.station_carrefour_market_la_poterie_e10`:

```yaml
value: 1.808
name: Carrefour Market La Poterie
brand: Carrefour Market
address: Boulevard Paul Hutin Desgrées
postal_code: 35200
city: Rennes
latitude: 48.091297777798
longitude: -1.6418527606305
updated_date: 2023-10-24 09:51:21
days_since_last_update: 0
unit_of_measurement: €
device_class: monetary
icon: mdi:gas-station
friendly_name: Station Carrefour Market La Poterie E10
```

## Nom et logo des stations

Si le nom d'une station n'apparait pas, vous pouvez contribuer en ajoutant les informations dans [le fichier stations_name.json](./custom_components/prix_carburant/stations_name.json).

Pour le logo [sensor.py](custom_components/prix_carburant/sensor.py), après `match self.station_info[ATTR_BRAND]:`.

## Exemples de configuration d'affichage dans Home Assistant

### via carte multiple-entity-row

Exemple de configuration avec [multiple-entity-row](https://github.com/benct/lovelace-multiple-entity-row):

![multiple-entity-row](readme_multipleentityrow.png)

```yaml
type: entities
entities:
  - entity: sensor.station_mastation_sp98
    type: custom:multiple-entity-row
    name: Ma Station
    show_state: false
    entities:
      - entity: sensor.station_mastation_e10
        name: E10
      - entity: sensor.station_mastation_sp98
        name: SP98
```

### via carte flex-table-card

![image](https://user-images.githubusercontent.com/44190435/176176400-47d20078-0105-46c2-8c81-ae58e58d08f4.png)

```yaml
type: custom:flex-table-card
clickable: true
sort_by: state
max_rows: 15
title: Gasoil
entities:
  include: sensor.station*gazole
columns:
  - name: nom station
    data: name, address
    multi_delimiter: <br />
  - name: dist.
    data: distance
  - name: prix
    data: state
  - name: Valid.
    data: days_since_last_update
    align: right
css:
  tbody tr:nth-child(1): 'color: #00ff00'
  tbody tr:nth-child(15): 'color: #f00020'
style: null
```

### via carte flex-table-card avec logo

Préparations:

- Pour rajouter les logos, utiliser File Editor, puis aller dans le dossier www, enfin créer un sous-dossier nommé « logos » par exemple. Dans ce dossier, vous devez charger les différents images representant les logos de vos stations service
- Puis éditer le fichier configuration.yaml, et rajouter et adapter pour chacune de vos stations (exemple ci-dessous avec 2 stations en gazole)

```yaml
homeassistant:
  customize:
    sensor.station_exemple1_gazole:
    entity_picture: /local/logos/carrefour.png
    sensor.station_exemple2_gazole:
    entity_picture: /local/logos/auchan.png
```

Enfin utiliser l’exemple de card comme ci-dessous

- optionel: Modifier le nom des entités pour éviter les noms de stations trop longs

![image](https://github.com/Aohzan/hass-prixcarburant/assets/44190435/eeb73a1d-13a1-486d-aeed-ff225c201295)

```yaml
type: custom:flex-table-card
sort_by: state+
clickable: true
entities:
  include:
    - sensor.station_carrefour_market_sp95
    - sensor.station_geant_casino_e10_2
    - sensor.station_intermarche_e10
    - sensor.station_relais_rond_point_j_rose_e10
columns:
  - data: entity_picture
    align: center
    icon: mdi:gas-station
    modify: '''<img src="'' + x + ''"style="height: 35px">'''
  - data: name
    name: ' Stations Le Creusot'
    align: left
  - icon: mdi:currency-eur
    data: state
    align: center
  - icon: mdi:calendar-clock
    data: days_since_last_update
    align: center
    prefix: J+
css:
  tbody tr:nth-child(odd): 'background-color: rgba(255, 255, 255, 0.2)'
  tbody tr:nth-child(even): 'background-color: rgba(255, 255, 255, 0.1)'
  tbody tr:nth-child(1): 'color: #00C62D; font-weight: bold'
  tbody tr:nth-child(4): 'color: #dd2c00'
card_mod: null
style: |
  :host {
    font-size: 18px;
    border-radius: 10px;
  }
```

### via carte map + auto-entities, dynamique

![image](https://user-images.githubusercontent.com/44190435/176176687-182eae11-7295-469e-8d43-beb951653d72.png)

```yaml
type: custom:auto-entities
card:
  type: map
  show_empty: false
filter:
  template: >
    [{% set ns = namespace(count=0) %} {% for x in expand(states.sensor)|
    sort(attribute='state')| map(attribute='entity_id') %} {% if 'station' in x
    and 'gazole'in x and ns.count < 20 %}'{{x}}',{% set ns.count = ns.count + 1
    %}{% endif %}{%- endfor %}]
```

### Deux carburants, via vertical-stack + flex-table card avec graphique

![image](https://user-images.githubusercontent.com/44190435/176178283-8050928b-39bf-4046-9789-17adb4e4d0a8.png)

```yaml
type: vertical-stack
cards:
  - type: picture
    image: /local/pictures/essence.jpg
  - type: custom:flex-table-card
    clickable: true
    sort_by: state
    max_rows: 5
    entities:
      include: sensor.station*gazole
    columns:
      - name: nom station
        data: name, address
        multi_delimiter: <br />
      - name: dist.
        data: distance
      - name: prix
        data: state
      - name: Valid.
        data: updated_date
        modify: Math.round((Date.now() - Date.parse(x)) / 36000 / 100 /24)
        align: left
        suffix: J
    css:
      tbody tr:nth-child(odd): 'background-color: rgba(255, 255, 255, 0.2)'
      tbody tr:nth-child(even): 'background-color: rgba(255, 255, 255, 0.1)'
      tbody tr:nth-child(1): 'color: #0033ff'
      tbody tr:nth-child(5): 'color: #FF0000'
    card_mod:
      style: |
        ha-card {
        border-radius: 10px;
        padding-bottom: 10px;
        background-color: rgba(0, 0, 0, 0.1)
        }
        :host {
        font-size: 13px;
        border-radius: 10px;
        }
  - type: custom:flex-table-card
    clickable: true
    sort_by: state
    max_rows: 5
    entities:
      include: sensor.station*E85
    columns:
      - name: nom station
        data: name, address
        multi_delimiter: <br />
      - name: dist.
        data: distance
      - name: prix
        data: state
      - name: Valid.
        data: updated_date
        modify: Math.round((Date.now() - Date.parse(x)) / 36000 / 100 /24)
        align: left
        suffix: J
    css:
      tbody tr:nth-child(odd): 'background-color: rgba(255, 255, 255, 0.2)'
      tbody tr:nth-child(even): 'background-color: rgba(255, 255, 255, 0.1)'
      tbody tr:nth-child(1): 'color: #0033ff'
      tbody tr:nth-child(5): 'color: #FF0000'
    card_mod:
      style: |
        ha-card {
        border-radius: 10px;
        background-color: rgba(0, 0, 0, 0.1)
        }
        :host {
        font-size: 13px;
        border-radius: 10px;
        }
card_mod:
  style: |
    ha-card {
     --ha-card-background: rgba(0, 0, 0, 0.1);
    ha-card {
      margin-top: 0em;
        }
```
