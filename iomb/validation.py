import iomb.model as model
import iomb.refmap as ref
import iomb.sat as sat
import iomb.ia as ia
import pandas as pd
import logging as log


class ValidationResult(object):
    def __init__(self):
        self.display_count = 5
        self.failed = False
        self.errors = []
        self.warnings = []
        self.information = []

    def fail(self, message):
        self.errors.insert(0, 'invalid model: ' + message)
        self.failed = True
        return self

    def __str__(self):
        t = 'Validation result:\n\n'
        c_errors, c_warnings = len(self.errors), len(self.warnings)
        if c_errors == 0 and c_warnings == 0:
            t += ' no errors or warnings, everything seems to be fine\n\n'
        else:
            t += ' there are %s errors and %s warnings\n\n' % (c_errors,
                                                               c_warnings)
        t += self._list_str('errors', self.errors)
        t += self._list_str('warnings', self.warnings)
        t += self._list_str('information', self.information)
        return t

    def _repr_html_(self):
        """ HTML representation of a validation result for the display in
            Jupyter workbooks. """
        t = '<div><h1>Validation result</h1>'
        c_errors, c_warnings = len(self.errors), len(self.warnings)
        if c_errors == 0 and c_warnings == 0:
            t += '<p style="color:#2E4172">no errors or warnings, everything ' \
                 'seems to be fine</p>'
        else:
            t += '<p style="color:#AA3939">there are %s errors and %s warnings' \
                 '</p>' % (c_errors, c_warnings)
        t += self._list_html('errors', self.errors, '#AA3939')
        t += self._list_html('warnings', self.warnings, '#C7C732')
        t += self._list_html('information', self.information, '#2E4172')
        t += '</div>'
        return t

    def _list_str(self, title: str, messages: list) -> str:
        if len(messages) == 0:
            return ''
        t = " %s:\n" % title
        for i in range(0, len(messages)):
            if self.display_count >= 0 and i >= self.display_count:
                r = len(messages) - self.display_count
                t += '  * %s more\n' % r
                break
            t += '  * %s\n' % messages[i]
        t += '\n'
        return t

    def _list_html(self, title: str, messages: list, color: str) -> str:
        if len(messages) == 0:
            return ''
        t = '<h3 style="color:%s">%s</h3><ul>' % (color, title)
        for i in range(0, len(messages)):
            if self.display_count >= 0 and i >= self.display_count:
                r = len(messages) - self.display_count
                t += '<li style="color:%s">%s more</li>' % (color, r)
                break
            t += '<li style="color:%s">%s</li>' % (color, messages[i])
        t += '</ul>'
        return t


def validate(m: model.Model) -> ValidationResult:
    log.info('validate model')
    vr = ValidationResult()
    if not isinstance(m, model.Model):
        return vr.fail('not an instance of iomb.model.Model')
    _check_field_types(m, vr)
    _check_sector_locations(m, vr)
    _check_ia_coverage(m, vr)
    return vr


def _check_field_types(m: model.Model, vr: ValidationResult):
    # field checks: (field value, type, field name, optional)
    field_checks = [
        (m.drc_matrix, pd.DataFrame, 'drc_matrix', False),
        (m.sat_table, sat.Table, 'sat_table', False),
        (m.sectors, ref.SectorMap, 'sectors', False),
        (m.ia_table, ia.Table, 'ia_table', True),
        (m.units, ref.UnitMap, 'units', True),
        (m.compartments, ref.CompartmentMap, 'compartments', True),
        (m.locations, ref.LocationMap, 'locations', True)
    ]
    for field in field_checks:
        value = field[0]
        optional = field[3]
        if optional and value is None:
            continue
        if not isinstance(value, field[1]):
            vr.fail('field %s is not an instance of %s' % (field[2], field[1]))
            break
    if m.ia_table is None:
        vr.information.append('model without LCIA data')


def _check_sector_locations(m: model.Model, vr: ValidationResult):
    """ Check if """
    unknown_codes = []
    for key in m.sectors.mappings.keys():
        sector = m.sectors.get(key)
        code = sector.location
        if code in unknown_codes:
            continue
        location = m.locations.get(code)
        if location is None:
            vr.warnings.append('unknown location %s' % code)
            unknown_codes.append(code)
    if len(unknown_codes) == 0:
        vr.information.append('all location codes of sectors are ok')


def _check_ia_coverage(m: model.Model, vr: ValidationResult):
    if m.ia_table is None:
        return
    uncovered_count = 0
    for flow in m.sat_table.flows:
        covered = False
        for category in m.ia_table.categories:
            factor = m.ia_table.get_factor(category, flow)
            if factor != 0:
                covered = True
                break
        if not covered:
            uncovered_count += 1
            vr.warnings.append('flow %s is not covered by the LCIA model' %
                               flow)
    if uncovered_count == 0:
        vr.information.append('all flows covered by LCIA model')

