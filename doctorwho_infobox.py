#!/usr/bin/env python3
import re
import time
import datetime
from pprint import pprint
import pywikibot
import mwparserfromhell

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

def enrich_entity_imdb(entity, infobox):
    if properties.imdb not in entity.text['claims']:
        print('\tTrying to set IMDB id for %s' % entity.id)
        if 'imdb_id' in [x.split('=')[0] for x in infobox.params]:
            imdb_id = 'tt' + infobox.get('imdb_id').split('=')[1].strip()
            set_property(entity, properties.imdb, imdb_id)
        else:
            print('\tNo IMDB id.')
    else:
        print('\tIMDB id already set')

def enrich_entity_target(entity, infobox, property, infobox_name,
        filter_=lambda x:x):
    if property not in entity.text['claims']:
        print('\tTrying to set property %s for %s' % (property, entity.id))
        value = infobox.get(infobox_name).split('=', 1)[1]
        value = filter_(value)
        for value_name in re.split(r'<br ?/?>', value):
            value_name = value_name.strip(' \'"\n')
            if not value_name:
                continue
            assert value_name.startswith('[['), repr(value_name)
            assert ']]' in value_name, value_name
            value_name = value_name[2:].split(']]', 1)[0]
            value_page = pywikibot.Page(enwiki, value_name)
            value = pywikibot.ItemPage.fromPage(value_page)
            set_property(entity, property, value)
    else:
        print('\t%s already set' % property)

def enrich_entity_previous(entity, previous):
    if properties.follows not in entity.text['claims']:
        print('\tTrying to set property "follows" for %s' % (entity.id,))
        set_property(entity, properties.follows, previous, imported=False)
    else:
        print('\t"follows" already set')
        assert entity.text['claims'][properties.follows][0].getTarget() == previous

def enrich_entity(entity, previous):
    if any(x not in entity.descriptions for x in ('en', 'fr')):
        descriptions = {
                'en': 'Doctor Who serial',
                'fr': 'épisode de Doctor Who',
                }
        descriptions.update(entity.descriptions)
        print('\tAdding description')
        entity.editEntity({'descriptions': descriptions})

    page = pywikibot.Page(site, entity.text['sitelinks']['enwiki'])
    templates = mwparserfromhell.parse('\n' + page.text).filter_templates()
    infoboxes = [x for x in templates
                 if x.name.strip() == 'Infobox Doctor Who episode']
    assert len(infoboxes) == 1, infoboxes
    infobox = infoboxes[0]

    # We use the filter for season 23, whose episodes links are like:
    # [[The Trial of a Time Lord]]: [[The Mysterious Planet]]
    enrich_entity_target(entity, infobox, properties.followedby, 'following',
            filter_=lambda x:x.split(':', 1)[-1])
    if previous:
        print('\tHas previous')
        enrich_entity_previous(entity, previous)

    enrich_entity_imdb(entity, infobox)
    enrich_entity_target(entity, infobox, properties.producer, 'producer')
    enrich_entity_target(entity, infobox, properties.screenwriter, 'writer')
    enrich_entity_target(entity, infobox, properties.director, 'director')

previous=None
entity = pywikibot.ItemPage(repo, 'Q1768718')
while True:
    print(entity.id)
    if entity.id == 'Q336240': # film
        continue
    if properties.series not in entity.text['claims'] and \
            entity.get()['descriptions'].get('en', None) == 'Doctor Who serial':
        set_property(entity, properties.series,
                pywikibot.ItemPage(repo, entities.doctorwho))
    else:
        assert entity.text['claims'][properties.series][0].getTarget().id == \
                entities.doctorwho
    enrich_entity(entity, previous)
    entity = pywikibot.ItemPage(repo, entity.id) # reload
    previous = entity
    try:
        entity = entity.text['claims'][properties.followedby][0].getTarget()
    except KeyError:
        print('Error: could not find “followed by” claim for %s' % entity.id)
        exit(1)
