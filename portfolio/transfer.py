"""Portfolio-only fixture validation and comparison, without exposing values."""
import hashlib
import json

from django.apps import apps
from django.core.management import CommandError


def canonical_fixture(records):
    models = {model._meta.label_lower: model
              for model in apps.get_app_config('portfolio').get_models()}
    result, seen = [], set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {'model', 'pk', 'fields'}:
            raise CommandError('Invalid portfolio fixture structure.')
        label, pk, fields = record['model'], record['pk'], record['fields']
        if label not in models or type(pk) is not int or pk < 1 or not isinstance(fields, dict):
            raise CommandError('Only portfolio models with positive integer PKs are allowed.')
        key = (label, pk)
        if key in seen:
            raise CommandError('Duplicate fixture primary key.')
        seen.add(key)
        meta = models[label]._meta
        expected = {f.name for f in meta.fields if f.serialize and not f.primary_key}
        expected.update(f.name for f in meta.many_to_many if f.serialize)
        if set(fields) != expected:
            raise CommandError('Fixture fields do not match the current models.')
        fields = dict(fields)
        if label == 'portfolio.proyecto':
            links = fields['technologies']
            if (not isinstance(links, list) or any(type(i) is not int for i in links)
                    or len(set(links)) != len(links)):
                raise CommandError('Invalid project/technology relationships.')
            fields['technologies'] = sorted(links)
        result.append({'model': label, 'pk': pk, 'fields': fields})
    for record in result:
        if record['model'] == 'portfolio.proyecto':
            if any(('portfolio.tecnologia', pk) not in seen
                   for pk in record['fields']['technologies']):
                raise CommandError('A project references a missing technology.')
        if record['model'] == 'portfolio.enlaceproyecto':
            if ('portfolio.proyecto', record['fields']['project']) not in seen:
                raise CommandError('An additional link references a missing project.')
    return sorted(result, key=lambda r: (r['model'], r['pk']))


def fixture_summary(records):
    records = canonical_fixture(records)
    encoded = json.dumps(records, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode('utf-8')
    counts = {model._meta.label_lower: 0
              for model in apps.get_app_config('portfolio').get_models()}
    for record in records:
        counts[record['model']] += 1
    return {'counts': counts, 'projectTechnologyRelations': sum(
        len(r['fields']['technologies']) for r in records if r['model'] == 'portfolio.proyecto'
    ), 'valuesAndRelationsSha256': hashlib.sha256(encoded).hexdigest()}
