#!/usr/bin/env python3
import time
import datetime
from pprint import pprint
import pywikibot

today = datetime.date.today()

# Some constants
class properties:
    imdb = 'P345'
    importedfrom = 'P143'
    retrieved = 'P813'
    follows = 'P155'
    followedby = 'P156'
    producer = 'P162'
    screenwriter = 'P58'
    director = 'P57'
    series = 'P179'
class entities:
    enwiki = 'Q328'
    doctorwho = 'Q34316'

enwiki = site = pywikibot.Site("en", "wikipedia")
wd = pywikibot.Site('wikidata', 'wikidata')
repo = wd.data_repository()

def set_property(entity, pid, value, imported=True):
    """Boilerplate for adding a claim and sourcing it."""
    # Add the claim
    claim = pywikibot.Claim(repo, pid)
    claim.setTarget(value)
    entity.addClaim(claim)

    if imported:
        # Instanciate the source
        statedin = pywikibot.Claim(repo, properties.importedfrom)
        itis = pywikibot.ItemPage(repo, entities.enwiki)
        statedin.setTarget(itis)

        # Instanciate the 'retrieved at' property
        retrieved = pywikibot.Claim(repo, properties.retrieved)
        date = pywikibot.WbTime(year=today.year,
                month=today.month, day=today.day)
        retrieved.setTarget(date)

        # Add the source
        claim.addSources([statedin, retrieved])

def enrich_entity_imdb(entity, page_data):
    if properties.imdb not in entity.text['claims']:
        print('Trying to set IMDB id for %s' % entity.id)
        if 'imdb_id' in page_data:
            imdb_id = 'tt' + page_data['imdb_id']
            set_property(entity, properties.imdb, imdb_id)
        else:
            print('No IMDB id.')
    else:
        print('IMDB id already set')

def enrich_entity_target(entity, page_data, property, infobox_name):
    if property not in entity.text['claims']:
        print('Trying to set property %s for %s' % (property, entity.id))
        for value_name in page_data[infobox_name].split('<br>'):
            assert value_name.startswith('[['), value_name
            assert ']]' in value_name, value_name
            value_name = value_name[2:].split(']]', 1)[0]
            print(value_name)
            value_page = pywikibot.Page(enwiki, value_name)
            print(value_page)
            value = pywikibot.ItemPage.fromPage(value_page)
            set_property(entity, property, value)
    else:
        print('%s already set' % property)

def enrich_entity_previous(entity, previous):
    if properties.follows not in entity.text['claims']:
        print('Trying to set property "follows" for %s' % (entity.id,))
        set_property(entity, properties.follows, previous, imported=False)
    else:
        print('"follows" already set')
        print(entity.text['claims'][properties.follows][0].getTarget())
        print(previous)
        assert entity.text['claims'][properties.follows][0].getTarget() == previous

def enrich_entity(entity, previous):
    page = pywikibot.Page(site, entity.text['sitelinks']['enwiki'])
    infobox = page.text \
            .split('\n{{Infobox Doctor Who episode\n', 1)[1] \
            .split('\n|}}\n', 1)[0]
    assert '{{' not in infobox
    page_data = dict(line.split('=') for line in infobox.split('\n|'))
    pprint(page_data)
    enrich_entity_imdb(entity, page_data)
    if previous:
        print('Has previous')
        enrich_entity_previous(entity, previous)
    enrich_entity_target(entity, page_data, properties.producer, 'producer')
    enrich_entity_target(entity, page_data, properties.screenwriter, 'writer')
    enrich_entity_target(entity, page_data, properties.director, 'director')

previous=None
entity = pywikibot.ItemPage(repo, 'Q1768718')
while True:
    print(entity.id)
    assert entity.text['claims'][properties.series][0].getTarget().id == \
            entities.doctorwho
    enrich_entity(entity, previous)
    if entity.id == 'Q1768716': # temporary
        break
    previous = entity
    entity = entity.text['claims'][properties.followedby][0].getTarget()
