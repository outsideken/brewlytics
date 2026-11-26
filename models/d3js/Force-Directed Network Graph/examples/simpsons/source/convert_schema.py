"""Draft nodes.csv + edges.csv from the one-table Simpsons edge list.

DRAFT FOR REVIEW: node types are guessed by rule, and labels are mapped to a
small set of relationships by hand (LABELS below). Both output files carry
review columns (`type_rule`, `original_labels`) to drop once checked.

    python examples/simpsons/source/convert_schema.py            # rewrites the example CSVs
    python examples/simpsons/source/convert_schema.py OUT_DIR    # writes them somewhere else (tests use this)

Schema
------
nodes.csv  id, name, type, aliases, deceased, notes, type_rule
edges.csv  from_id, to_id, relationship, label, category, directed, status,
           role, detail, source, original_labels

* One row per fact. Reverse-worded duplicates (Husband of / Wife of, Father
  of / Son of) collapse into one row; the reverse wording is derived from
  `relationship`.
* Symmetric relationships (sibling_of, spouse_of, ...) have directed=False and
  from_id < to_id.
* Aliases ("Also known as", stage names, boxing names, patriot names) are node
  columns, not edges. Self-referencing rows ("Has a Glass Eye") become notes.
* "Deceased X of" / "(Deceased)" / "Widow of" set `deceased` on the right node.
* `source` is blank except for facts checked against a cited page
  (ROW_SOURCES / ROW_OVERRIDES / EXTRA_EDGES).
"""

import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent          # example/source/
SRC = HERE / 'brew - The Simpsons (2026-11-26) corrected.csv'
OUT_DIR = HERE.parent                           # example/

## relationship -> (category, symmetric)
RELATIONSHIPS = {
    'parent_of':          ('family', False),
    'grandparent_of':     ('family', False),
    'aunt_or_uncle_of':   ('family', False),
    'sibling_of':         ('family', True),
    'cousin_of':          ('family', True),
    'in_law_of':          ('family', True),
    'spouse_of':          ('romance', True),
    'engaged_to':         ('romance', True),
    'romantic_with':      ('romance', True),
    'crush_on':           ('romance', False),
    'friend_of':          ('social', True),
    'neighbour_of':       ('social', True),
    'rival_of':           ('social', True),
    'colleague_of':       ('work', True),
    'works_at':           ('work', False),
    'works_for':          ('work', False),
    'student_at':         ('school', False),
    'member_of':          ('membership', False),
    'frequents':          ('membership', False),
    'owns':               ('ownership', False),
    'has_pet':            ('ownership', False),
    'appears_in':         ('media', False),
    'created':            ('media', False),
    'likes':              ('social', False),
    'mentor_of':          ('social', False),
    'part_of':            ('structure', False),
    'lives_in':           ('place', False),
    'died_in':            ('event', False),
    'story_event':        ('story', False),
}

ALIAS = 'ALIAS'  # label marks the second name as another name for the first

## label -> (relationship, flip, status, role, deceased)
##   flip      True: the fact reads to -> from ("Bart Son of Homer" = Homer parent_of Bart)
##   deceased  'from' / 'to': which end of the row is dead
##   story_event rows keep the label as `detail`
L = lambda rel, flip=False, status='', role='', deceased=None: (rel, flip, status, role, deceased)
LABELS = {
    # aliases
    'Also known as': ALIAS, 'Also Known as': ALIAS, 'Formerly Known as': ALIAS,
    'Be Sharps Stage Name': ALIAS, 'Professionally Boxed as': ALIAS,
    'Temporary Patriot Name': ALIAS,
    'Apu\'s Stage Name': L('member_of'),  # the stage name itself is an alias
    # parents
    'Father of': L('parent_of'), 'Mother of': L('parent_of'),
    'Deceased Father of': L('parent_of', deceased='from'),
    'Deceased Mother of': L('parent_of', deceased='from'),
    'Son of': L('parent_of', True), 'Daughter of': L('parent_of', True),
    'Illegitimate daughter of': L('parent_of', True, role='illegitimate'),
    'Adopted': L('parent_of', role='adoptive'),
    'Adoptive Father of': L('parent_of', role='adoptive'),
    'Adoptive Mother of': L('parent_of', role='adoptive'),
    'Adopted Son of': L('parent_of', True, role='adoptive'),
    'Step-Father of': L('parent_of', role='step'),
    'Step-Son of': L('parent_of', True, role='step'),
    'Grandpa': L('grandparent_of'),
    'Paternal Grandfather': L('grandparent_of'),  # gender-neutral label: no paternal/maternal
    'Aunt of': L('aunt_or_uncle_of'), 'Uncle of': L('aunt_or_uncle_of'),
    'Nephew of': L('aunt_or_uncle_of', True), 'Niece of': L('aunt_or_uncle_of', True),
    # siblings, cousins, in-laws
    'Brother of': L('sibling_of'), 'Sister of': L('sibling_of'),
    'Twin Brother of': L('sibling_of', role='twin'), 'Twin Sister of': L('sibling_of', role='twin'),
    'Half-Brother of': L('sibling_of', role='half'), 'Half-Sister of': L('sibling_of', role='half'),
    'Cousin of': L('cousin_of'),
    'Brother-in-Law': L('in_law_of'),
    'Deceased Sister-in-Law': L('in_law_of', deceased='from'),
    # marriage
    'Husband of': L('spouse_of'), 'Wife of': L('spouse_of'), 'Married to': L('spouse_of'),
    'Also Married': L('spouse_of'),
    'Briefly Married to': L('spouse_of', role='brief'),
    'Husband of (Divorced)': L('spouse_of', status='divorced'),
    'Wife of (divorced)': L('spouse_of', status='divorced'),
    'Married to (Divorced)': L('spouse_of', status='divorced'),
    'Divorced': L('spouse_of', status='divorced'),
    'Divorced from': L('spouse_of', status='divorced'),
    'Formerly Married to': L('spouse_of', status='divorced'),
    'Husband of (Annulled)': L('spouse_of', status='annulled'),
    'Wife of (Annulled)': L('spouse_of', status='annulled'),
    'Husband of (Deceased)': L('spouse_of', status='widowed', deceased='to'),
    'Deceased Husband of': L('spouse_of', status='widowed', deceased='from'),
    'Deceased Wife of': L('spouse_of', status='widowed', deceased='from'),
    'Widow of': L('spouse_of', status='widowed', deceased='to'),
    'Pretended to be Married to': L('story_event'),
    # engagement, dating
    'Ex-Fiance': L('engaged_to', status='ended'), 'Ex-Fiancee': L('engaged_to', status='ended'),
    'Almost Married': L('engaged_to', status='ended', role='almost married'),
    'Dated': L('romantic_with', role='dated'),
    'Once dated': L('romantic_with', status='ended', role='dated'),
    'Once Dated': L('romantic_with', status='ended', role='dated'),
    'Had a single date with': L('romantic_with', status='ended', role='single date'),
    'Boyfriend of': L('romantic_with', role='dating'),
    'Girlfriend of': L('romantic_with', role='dating'),
    'Ex-Boyfriend of': L('romantic_with', status='ended', role='dating'),
    'Ex-Girlfriend of': L('romantic_with', status='ended', role='dating'),
    'First Girlfriend': L('romantic_with', status='ended', role='first partner'),
    'Had a relationship with': L('romantic_with', status='ended', role='relationship'),
    'Briefly Romantically Connected With': L('romantic_with', status='ended', role='brief'),
    'Once Romantically Linked': L('romantic_with', status='ended', role='brief'),
    'Only Serious Relationship with a Woman': L('romantic_with', status='ended', role='relationship'),
    'Hooked up with': L('romantic_with', role='hooked up'),
    'Slept with': L('romantic_with', role='slept with'),
    'Made out with': L('romantic_with', role='made out'),
    'Makes out with': L('romantic_with', role='made out'),
    'Went to Prom with': L('romantic_with', status='ended', role='prom date'),
    'Dated to make Bart Jealous': L('romantic_with', status='ended', role='dated'),
    'Fathered a Litter of Puppies with': L('romantic_with', role='litter of puppies'),
    'Has a Crush on': L('crush_on'), 'First Crush': L('crush_on', role='first crush'),
    'Proposed to': L('story_event'),
    # social
    'Best Friend of': L('friend_of', role='best friend'),
    'Friends with': L('friend_of'),
    'Ex-Friend of': L('friend_of', status='ended'),
    'Neighbor of': L('neighbour_of'),
    'Irish Rival': L('rival_of'), 'Scottish Rival': L('rival_of'),
    'Ongoing Feud with': L('rival_of', role='feud'),
    'Biggest Fan': L('likes', role='biggest fan'),
    'Loves': L('likes', role='loves'),
    'Mentored': L('mentor_of'),
    'Learned Jazz from': L('mentor_of', True, role='jazz'),
    'Works with': L('colleague_of'),
    # work
    'Works at': L('works_at'), 'Worked at': L('works_at', status='former'),
    'Former Employee': L('works_at', status='former'),
    'Former Groundskeeper': L('works_at', status='former', role='groundskeeper'),
    'Former Principal of': L('works_at', status='former', role='principal'),
    'Former School Cook': L('works_at', status='former', role='school cook'),
    'Principal': L('works_at', role='principal'),
    'Groundskeeper': L('works_at', role='groundskeeper'),
    'Art Teacher': L('works_at', role='art teacher'),
    'Coding Teacher': L('works_at', role='coding teacher'),
    'Debate Team Teacher': L('works_at', role='debate team teacher'),
    'Gym Teacher': L('works_at', role='gym teacher'),
    'Music Teacher': L('works_at', role='music teacher'),
    'Second Grade Teacher': L('works_at', role='second grade teacher'),
    'Teaches at': L('works_at', role='teacher'),
    "Bart's Teacher": L('works_at', role="Bart's teacher"),
    'Cafeteria Chef': L('works_at', role='cafeteria chef'),
    'School Nurse': L('works_at', role='school nurse'),
    'School Bus Driver': L('works_at', role='school bus driver'),
    'School District Psychologist': L('works_at', role='school district psychologist'),
    "Principal Skinner's Secretary": L('works_at', role='secretary'),
    'Security Guard at': L('works_at', role='security guard'),
    'Manager at': L('works_at', role='manager'),
    'Proprietor/Bartender': L('owns', role='proprietor/bartender'),
    'Proprietor/Owner': L('owns', role='proprietor'),
    'Superintendent of': L('works_at', role='superintendent'),
    'Anchor': L('works_at', role='anchor'),
    'Traffic Reporter': L('works_at', role='traffic reporter'),
    'Weather Lady': L('works_at', role='weather presenter'),
    'Professor at': L('works_at', role='professor'),
    'Reverend': L('works_at', role='reverend'),
    'Head of': L('works_at', role='head'),
    'Host of': L('works_at', role='host'),
    'Former Tester and Current Commissioner': L('works_at', role='commissioner (former tester)'),
    'Spokesperson': L('works_for', role='spokesperson'),
    'Executive Personal Assistant': L('works_for', role='executive personal assistant'),
    'Boss of': L('works_for', True),          # A boss of B = B works for A
    'Nanny for': L('works_for', role='nanny'),  # the nanny works for the child
    'Coach': L('member_of', role='coach'),
    # school
    'Student at': L('student_at'),
    'School Bully': L('student_at', role='school bully'),
    'Attended': L('student_at', status='former'),
    'Attended as a young girl': L('student_at', status='former'),
    'Attended Bartending School at': L('student_at', status='former', role='bartending school'),
    'Earning his Doctorate at': L('student_at', role='doctorate'),
    'Graduated from': L('student_at', status='graduated'),
    'Graduated 1st in Class of 7 Million': L('student_at', status='graduated', role='1st in class of 7 million'),
    'Accepted as student, but acceptance letter frozen at top of Mt. Springfield': L('story_event', True),
    'Taught': L('works_at', role='teacher'),
    'Teaches class on "How to Chew Tobacco"': L('works_at', role='teaches "How to Chew Tobacco"'),
    # membership
    'Member of': L('member_of'),
    'Player': L('member_of', role='player'),
    'Team Captain': L('member_of', role='team captain'),
    'Lead Vocals': L('member_of', role='lead vocals'),
    'Main Vocals 1': L('member_of', role='main vocals'),
    'Main Vocals 2': L('member_of', role='main vocals'),
    'Sub Vocals': L('member_of', role='sub vocals'),
    'Lead Singer of': L('member_of', role='lead singer'),
    'Band Manager': L('member_of', role='band manager'),
    'Private': L('member_of', role='private'),
    'Private 5th Class': L('member_of', role='private 5th class'),
    'Radio Operator': L('member_of', role='radio operator'),
    'Unit Commander': L('member_of', role='unit commander'),
    'Leader of the': L('member_of', role='leader'),
    'Founded': L('member_of', role='founder'),
    'Once attended': L('member_of', status='former'),
    'Newsreader': L('member_of', role='newsreader'),
    "Bart's People Newsreader": L('member_of', role="newsreader (Bart's People)"),
    'Represented Japan': L('member_of', role='represented Japan'),
    'Radioshow Cohosts': L('member_of', role='co-host'),
    'Frequent': L('frequents'),
    'Favorite Restaurant': L('frequents', role='favourite restaurant'),
    'Hosts meetings at church': L('story_event'),
    # ownership
    'Owns': L('owns'), 'Owns a': L('owns'),
    'Owned a': L('owns', status='former'), 'Owned the': L('owns', status='former'),
    'Once Owned': L('owns', status='former'),
    'Pet': L('has_pet'), 'Pet Border Collie': L('has_pet', role='border collie'),
    'Pet Dog (Deceased)': L('has_pet', role='dog', deceased='to'),
    'Pet Iguana': L('has_pet', role='iguana'), 'Pet Poodle': L('has_pet', role='poodle'),
    'Feeds': L('story_event'), 'Buys': L('story_event'),
    # media
    'Starred in': L('appears_in', role='star'),
    'Appeared on': L('appears_in'),
    'Co-Star': L('appears_in', role='co-star'),
    'Hosts': L('appears_in', role='host'),
    'Once a Presenter': L('appears_in', role='presenter'),
    'Played': L('appears_in', role='played'),
    'Played Lead Role in Movie version of Comic Book Series': L('appears_in', role='lead role (movie)'),
    'Character on TV Show': L('part_of'),
    'Album': L('created', role='album'), 'Single': L('created', role='single'),
    'Co-Developer of': L('created', role='co-developer'),
    'Wrote Movie Script': L('created', role='screenwriter'),
    'Wrote a Series of Mystery Novels, one titled': L('created', role='novelist'),
    # structure, place, events
    'In': L('part_of'), 'Team': L('part_of'),
    'Educational Programming': L('part_of', role='educational programming'),
    'New Detention Center for': L('part_of', role='detention centre'),
    'Lives in': L('lives_in'), 'Lives at': L('lives_in'),
    'Killed in': L('died_in', deceased='from'),
    'Killed by T-Shirt Cannon at': L('died_in', role='killed by T-shirt cannon', deceased='from'),
}
## one-off plot points: kept as story_event with the label as detail
for label in ['Bullied', 'Fired', 'Punched in face', 'Rescued', 'Treats',
              'Plotted to kill', 'Framed for Armed Robbery', 'Replaced',
              'Discovered Sideshow Bob\'s Plot to kill Selma',
              'Discovered that Veronica actually a man in disguise',
              'Incorrectly pronounced as dead',
              'Once Punched and no longer allowed to judge contests',
              'Invited to School Debate Team', 'Recruited to form a Boy Band',
              'Sent to visit after telling false story about Dark Stanley',
              'Sent to Private School after caught Kissing Milhouse',
              'Tried to get to move in',
              'Plaintiff in Paternity Suit (with 36 other women)',
              'Blames for getting fired', 'Played Lisa\'s Song',
              'Wins the elephant in a radio contest called "KBBL Is Gonna Gimme Something Stupid"',
              'Worked as a male stripper to pay for Med school',
              'Sharply criticized, comparing their failure to transform the town to his own failure to formulate a unified field theory']:
    LABELS[label] = L('story_event')

## Per-row overrides where one label means different things: (from, label, to) -> (spec, source)
JUB_JUB = 'https://simpsons.fandom.com/wiki/Jub-Jub_Bouvier'
ROW_OVERRIDES = {
    # Selma adopted a pet iguana, not a child (cf. Selma "Adopted" Ling)
    ('Selma Bouvier', 'Adopted', 'Jub-Jub'): (L('has_pet', role='iguana (adopted)'), JUB_JUB),
    # Gladys owned him first and has died
    ('Aunt Gladys', 'Pet Iguana', 'Jub-Jub'): (L('has_pet', status='former', role='iguana', deceased='from'), JUB_JUB),
}

## Sources for rows checked against a page, mapping unchanged: (from, label, to) -> URL
DEWEY_LARGO = 'https://simpsons.fandom.com/wiki/Dewey_Largo'
BERNICE = 'https://simpsons.fandom.com/wiki/Bernice_Hibbert'
ROW_SOURCES = {
    # two different men, both named Dewey ("Flaming Moe")
    ('Dewey Largo', 'Ex-Boyfriend of', 'Dewey'): DEWEY_LARGO,
    ('Dewey', 'Ex-Boyfriend of', 'Dewey Largo'): DEWEY_LARGO,
    ('Juilliard School of Music', 'Accepted as student, but acceptance letter frozen at top of Mt. Springfield', 'Dewey Largo'): DEWEY_LARGO,
    ('Dewey Largo', 'Music Teacher', 'Springfield Elementary School'): DEWEY_LARGO,
    ('Dewey Largo', 'Works at', 'Starving Teachers Moving Co.'): DEWEY_LARGO,
    ('Bernice Hibbert', 'Sister of', 'Chester Dupree'): BERNICE,
    ('Chester Dupree', 'Brother of', 'Bernice Hibbert'): BERNICE,
}

## Facts that are not in the source CSV: (from, to, spec, source)
EXTRA_EDGES = [
    # Gladys left Jub-Jub to Jacqueline before he went to Patty and Selma
    ('Jacqueline Bouvier', 'Jub-Jub', L('has_pet', status='former', role='iguana (inherited)'), JUB_JUB),
    # current boyfriend ("Girl's in the Band"; still together as of season 35)
    ('Dewey Largo', 'Geoffrey', L('romantic_with', role='dating'), DEWEY_LARGO),
]

## Display labels (gender-neutral; read from -> to). Edit a row's `label` in
## edges.csv to override.
BASE_LABELS = {
    'parent_of': 'parent of', 'grandparent_of': 'grandparent of',
    'aunt_or_uncle_of': 'aunt/uncle of', 'sibling_of': 'sibling of',
    'cousin_of': 'cousin of', 'in_law_of': 'in-law of', 'spouse_of': 'spouse of',
    'engaged_to': 'engaged to', 'romantic_with': 'romance with', 'crush_on': 'crush on',
    'friend_of': 'friend of', 'neighbour_of': 'neighbour of', 'rival_of': 'rival of',
    'colleague_of': 'colleague of', 'works_at': 'works at', 'works_for': 'works for',
    'student_at': 'student at', 'member_of': 'member of', 'frequents': 'frequents',
    'owns': 'owns', 'has_pet': 'has pet', 'likes': 'likes', 'mentor_of': 'mentor of',
    'appears_in': 'appears in', 'created': 'created', 'part_of': 'part of',
    'lives_in': 'lives in', 'died_in': 'died in',
}
## (relationship, role or status) -> label, where the general rules read badly
LABEL_OVERRIDES = {
    ('parent_of', 'illegitimate'): 'parent of (illegitimate)',
    ('parent_of', 'step'): 'step-parent of',
    ('sibling_of', 'twin'): 'twin of', ('sibling_of', 'half'): 'half-sibling of',
    ('spouse_of', 'brief'): 'briefly married to', ('spouse_of', 'divorced'): 'ex-spouse of',
    ('spouse_of', 'annulled'): 'annulled marriage', ('spouse_of', 'widowed'): 'spouse of (widowed)',
    ('engaged_to', 'almost married'): 'almost married', ('engaged_to', 'ended'): 'ex-fiancé(e) of',
    ('romantic_with', 'dated'): 'dated', ('romantic_with', 'dating'): 'dating',
    ('romantic_with', 'relationship'): 'relationship with', ('romantic_with', 'brief'): 'brief romance with',
    ('romantic_with', 'slept with'): 'slept with', ('romantic_with', 'hooked up'): 'hooked up with',
    ('romantic_with', 'made out'): 'made out with', ('romantic_with', 'single date'): 'one date with',
    ('romantic_with', 'prom date'): 'prom date of', ('romantic_with', 'first partner'): 'first partner of',
    ('romantic_with', 'litter of puppies'): 'puppies with',
    ('crush_on', 'first crush'): 'first crush',
    ('friend_of', 'best friend'): 'best friend of', ('friend_of', 'ended'): 'ex-friend of',
    ('rival_of', 'feud'): 'feuds with',
    ('likes', 'biggest fan'): 'biggest fan of', ('likes', 'loves'): 'loves',
    ('mentor_of', 'jazz'): 'jazz mentor of',
    ('student_at', 'former'): 'attended', ('student_at', 'graduated'): 'graduated from',
    ('student_at', 'school bully'): 'bully at', ('student_at', 'doctorate'): 'doctoral student at',
    ('student_at', 'bartending school'): 'bartending student at',
    ('student_at', '1st in class of 7 million'): 'top of class at',
    ('member_of', 'coach'): 'coach of', ('member_of', 'founder'): 'founder of',
    ('member_of', 'leader'): 'leader of', ('member_of', 'band manager'): 'manager of',
    ('member_of', 'team captain'): 'captain of', ('member_of', 'former'): 'former member of',
    ('frequents', 'favourite restaurant'): 'favourite restaurant',
    ('owns', 'proprietor'): 'proprietor of', ('owns', 'proprietor/bartender'): 'owner/bartender of',
    ('owns', 'former'): 'owned',
    ('appears_in', 'star'): 'starred in', ('appears_in', 'co-star'): 'co-star of',
    ('appears_in', 'host'): 'host of', ('appears_in', 'played'): 'played',
    ('appears_in', 'presenter'): 'presenter at', ('appears_in', 'lead role (movie)'): 'lead in',
    ('created', 'album'): 'album', ('created', 'single'): 'single',
    ('created', 'co-developer'): 'co-developed', ('created', 'novelist'): 'wrote',
    ('created', 'screenwriter'): 'wrote',
    ('part_of', 'educational programming'): 'programme on', ('part_of', 'detention centre'): 'detention centre for',
    ('died_in', 'killed by T-shirt cannon'): 'killed at',
    ('works_at', 'former'): 'worked at', ('works_at', 'head'): 'head of',
    ('works_at', 'host'): 'host of', ('works_at', 'superintendent'): 'superintendent of',
    ('member_of', "newsreader (Bart's People)"): 'newsreader in',
}
ROLE_CONNECTOR = {'works_at': 'at', 'works_for': 'for', 'member_of': 'in'}  # "<role> at/for/in"
ROLE_ADJECTIVE = {'parent_of', 'grandparent_of'}                            # "<role> parent of"

## story_event detail -> short label for the graph (full wording stays in `detail`)
STORY_LABELS = {
    'Accepted as student, but acceptance letter frozen at top of Mt. Springfield': 'accepted (letter lost)',
    'Blames for getting fired': 'blames',
    'Bullied': 'bullied',
    'Buys': 'buys',
    "Discovered Sideshow Bob's Plot to kill Selma": 'foiled plot of',
    'Discovered that Veronica actually a man in disguise': 'unmasked',
    'Feeds': 'feeds',
    'Fired': 'fired',
    'Framed for Armed Robbery': 'framed',
    'Hosts meetings at church': 'hosts',
    'Incorrectly pronounced as dead': 'misdeclared dead',
    'Invited to School Debate Team': 'invited',
    'Once Punched and no longer allowed to judge contests': 'punched',
    'Plaintiff in Paternity Suit (with 36 other women)': 'paternity suit',
    "Played Lisa's Song": 'played at',
    'Plotted to kill': 'plotted to kill',
    'Pretended to be Married to': 'fake marriage',
    'Proposed to': 'proposed to',
    'Punched in face': 'punched',
    'Recruited to form a Boy Band': 'recruited',
    'Replaced': 'replaced',
    'Rescued': 'rescued',
    'Sent to Private School after caught Kissing Milhouse': 'sent to',
    'Sent to visit after telling false story about Dark Stanley': 'sent to',
    'Sharply criticized, comparing their failure to transform the town to his own failure to formulate a unified field theory': 'criticized',
    'Treats': 'treats',
    'Tried to get to move in': 'courted',
    'Wins the elephant in a radio contest called "KBBL Is Gonna Gimme Something Stupid"': 'won',
    'Worked as a male stripper to pay for Med school': 'worked as',
}


## (relationship, role, status) -> label, checked first
COMBO_LABELS = {
    ('romantic_with', 'dating', 'ended'): 'ex of',
}


def make_label(rel, status, role, detail):
    """Short, gender-neutral display text for one edge (reads from -> to).

    Order: story short label; role+status combination; role override or
    role rule (prefixed "former" when status is former); status override;
    base wording.
    """
    if rel == 'story_event':
        return STORY_LABELS[detail]
    if (rel, role, status) in COMBO_LABELS:
        return COMBO_LABELS[(rel, role, status)]
    if role:
        if (rel, role) in LABEL_OVERRIDES:
            text = LABEL_OVERRIDES[(rel, role)]
        elif rel in ROLE_ADJECTIVE:
            text = '%s %s' % (role, BASE_LABELS[rel])
        elif rel in ROLE_CONNECTOR:
            text = '%s %s' % (role, ROLE_CONNECTOR[rel])
        elif rel == 'has_pet':
            text = 'pet %s' % role
        else:
            text = BASE_LABELS[rel]
        return 'former ' + text if status == 'former' else text
    if status and (rel, status) in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[(rel, status)]
    return 'former ' + BASE_LABELS[rel] if status == 'former' else BASE_LABELS[rel]


## node type rules: relationship -> type for the node at that end
TYPE_FROM_TARGET = {
    'works_at': 'Organisation', 'student_at': 'Organisation', 'member_of': 'Organisation',
    'frequents': 'Place', 'has_pet': 'Animal', 'appears_in': 'Media', 'created': 'Media',
    'lives_in': 'Place', 'died_in': 'Event',
}
TYPE_OVERRIDES = {  # where the rules can't tell
    'Pork Rinds': 'Thing', 'Mercedes-Benz G500': 'Thing', 'Volvo 850 Sedan': 'Thing',
    'Ferrari F40': 'Thing', 'Hummer H1': 'Thing', 'Saturn SC Coupe': 'Thing',
    'PowerSauce Energy Bar': 'Thing', 'Stampy': 'Animal', 'Rosa Barks': 'Animal',
    'Santa\'s Little Helper': 'Animal', 'Snowball V': 'Animal', 'Jub-Jub': 'Animal',
    'Springfield Nuclear Power Plant': 'Organisation', 'Kwik-E-Mart': 'Organisation',
    'Krusty Burger': 'Organisation', 'The Leftorium': 'Organisation',
    'Austin Celtics Basketball Team': 'Organisation', 'The Android\'s Dungeon': 'Organisation',
    "Moe's Tavern": 'Place', 'Springfield Speedway': 'Place', 'The Jazz Hole': 'Place',
    'Springfield School District': 'Organisation', 'Springfield Peewee Hockey League': 'Organisation',
    'Kidz News': 'Media', 'Smelly': 'Character',
    'Consequences Eradicator (Conrad) App': 'Thing', 'Model United Nations': 'Organisation',
    'Remote Onsite Correctional Center': 'Organisation', 'Juilliard School of Music': 'Organisation',
    'Saint Sebastian\'s School for Wicked Girls': 'Organisation',
    'Springfield Alcoholics Anonymous': 'Organisation', 'Academy Awards': 'Event',
    '"How to Strip for your Wife" Course': 'Event', 'Gabbin\' about God Radio Talk Show': 'Media',
    'Blind Willie': 'Character', 'Party Posse': 'Organisation', 'Mighty Pigs': 'Organisation',
    'Kwik-E-Mart Gougers': 'Organisation', 'Malcom Sex': 'Character',
}


def slug(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def read_rows(path):
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))[1:]
    return [(a.strip(), e.strip(), b.strip()) for a, b, e, *_ in rows if a.strip() and b.strip()]


def canonical_lookup(rows):
    parent = {b: a for a, e, b in rows if LABELS.get(e) == ALIAS}

    def root(n):
        seen = set()
        while n in parent and n not in seen:
            seen.add(n)
            n = parent[n]
        return n
    return {alias: root(alias) for alias in parent}


def convert(rows):
    unmapped = sorted({e for a, e, b in rows if a != b and e not in LABELS})
    if unmapped:
        raise SystemExit('Unmapped labels: %s' % unmapped)
    canon = canonical_lookup(rows)
    name = lambda n: canon.get(n, n)

    aliases, notes, deceased = defaultdict(list), defaultdict(list), set()
    for alias, c in sorted(canon.items()):
        aliases[c].append(alias)

    facts = [(a, label, b) + ROW_OVERRIDES.get((a, label, b), (LABELS.get(label), ROW_SOURCES.get((a, label, b), '')))
             for a, label, b in rows]
    unused = set(ROW_SOURCES) - set(rows)
    if unused:
        raise SystemExit('ROW_SOURCES rows not in the CSV: %s' % sorted(unused))
    facts += [(a, '(added)', b, spec, source) for a, b, spec, source in EXTRA_EDGES]

    edges = dict()
    for a, label, b, spec, source in facts:
        if a == b:  # a fact about one node: a note, whatever the label
            notes[name(a)].append(label)
            if label.lower().startswith('killed'):
                deceased.add(name(a))
            continue
        if spec == ALIAS:
            continue
        rel, flip, status, role, dead = spec
        a, b = name(a), name(b)
        if dead:
            deceased.add(a if dead == 'from' else b)
        if a == b:
            notes[a].append(label)
            continue
        if flip:
            a, b = b, a
        category, symmetric = RELATIONSHIPS[rel]
        if symmetric:
            a, b = sorted((a, b), key=slug)
        detail = label if rel == 'story_event' else ''
        key = (a, b, rel, detail) if rel == 'story_event' else (a, b, rel)
        e = edges.setdefault(key, {'from': a, 'to': b, 'relationship': rel, 'category': category,
                                   'directed': not symmetric, 'status': set(), 'role': set(),
                                   'detail': detail, 'labels': [], 'source': set()})
        if source:
            e['source'].add(source)
        if status:
            e['status'].add(status)
        if role:
            e['role'].add(role)
        e['labels'].append(label)

    names = sorted({x for e in edges.values() for x in (e['from'], e['to'])} | set(notes), key=slug)
    ntype, rule = dict(), dict()
    for n in names:
        if n in TYPE_OVERRIDES:
            ntype[n], rule[n] = TYPE_OVERRIDES[n], 'override'
    for e in edges.values():
        t = TYPE_FROM_TARGET.get(e['relationship'])
        if t and e['to'] not in ntype:
            ntype[e['to']], rule[e['to']] = t, 'target of %s' % e['relationship']
    for n in names:
        ntype.setdefault(n, 'Character')
        rule.setdefault(n, 'default')

    ids = {n: slug(n) for n in names}
    assert len(set(ids.values())) == len(ids), 'slug collision'

    node_rows = [{'id': ids[n], 'name': n, 'type': ntype[n], 'aliases': '; '.join(aliases.get(n, [])),
                  'deceased': 'Y' if n in deceased else '', 'notes': '; '.join(notes.get(n, [])),
                  'type_rule': rule[n]} for n in names]
    for e in edges.values():
        # one display label per edge; several roles/statuses read as "a; b"
        roles = sorted(e['role']) or ['']
        e['label'] = '; '.join(sorted({make_label(e['relationship'], '; '.join(sorted(e['status'])), r, e['detail'])
                                       for r in roles}))
    edge_rows = [{'from_id': ids[e['from']], 'to_id': ids[e['to']], 'relationship': e['relationship'],
                  'label': e['label'], 'category': e['category'], 'directed': e['directed'],
                  'status': '; '.join(sorted(e['status'])), 'role': '; '.join(sorted(e['role'])),
                  'detail': e['detail'], 'source': '; '.join(sorted(e['source'])), 'original_labels': ' | '.join(e['labels'])}
                 for e in sorted(edges.values(), key=lambda e: (e['category'], e['relationship'], slug(e['from']), slug(e['to'])))]
    return node_rows, edge_rows


def write(path, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def main(out_dir=OUT_DIR):
    out_dir = Path(out_dir)
    rows = read_rows(SRC)
    nodes, edges = convert(rows)
    write(out_dir / 'nodes.csv', nodes)
    write(out_dir / 'edges.csv', edges)
    from collections import Counter
    print('%d source rows -> %d nodes, %d edges' % (len(rows), len(nodes), len(edges)))
    print('node types:', dict(Counter(n['type'] for n in nodes).most_common()))
    print('relationships:', len({e['relationship'] for e in edges}), dict(Counter(e['category'] for e in edges).most_common()))
    print('aliases on nodes:', sum(bool(n['aliases']) for n in nodes), '; deceased:', sum(n['deceased'] == 'Y' for n in nodes),
          '; with notes:', sum(bool(n['notes']) for n in nodes))
    print('edges merged from >1 source row:', sum(' | ' in e['original_labels'] for e in edges))


if __name__ == '__main__':
    main(*sys.argv[1:2])
