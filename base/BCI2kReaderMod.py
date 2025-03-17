#adapted from BCI2kReader: https://github.com/neurotechcenter/BCI2kReader

import sys
import io

def GetLine(stream, e = b'\n'):
    line = []
    c = stream.read(1)
    while (c != b'' and c != e):
        line.append(c)
        c = stream.read(1)
    return str(b''.join(line), 'utf-8')

def GetParamToken(stream):
    c = stream.read(1)
    while (c == b' '):
        c = stream.read(1)
    t = []
    while (c != b'' and c != b' '):
        t.append(c)
        c = stream.read(1)
    return str(b''.join(t), 'utf-8')


def unescape(s):
    # unfortunately there are two slight difference between the BCI2000 standard and urllib.unquote
    if s in ['%', '%0', '%00']: return ''  # here's one (empty string)
    out = ''
    s = list(s)
    while len(s):
        c = s.pop(0)
        if c == '%':
            c = ''.join(s[:2])
            if c.startswith('%'):  # here's the other ('%%' maps to '%')
                out += '%'
                s = s[1:]
            else:
                try:
                    c = int(c, 16)
                except:
                    pass
                else:
                    out += chr(c)
                    s = s[2:]
        else:
            out += c
    return out

def Warn(msg):
    #MUTE WARNINGS
    return
    #print('WARNING: %s' % msg)
    sys.stderr.write('WARNING: %s\n' % msg)
    try:
        sys.stderr.flush()
    except:
        pass
    
class DatFileError(Exception): pass

def ParseParam(stream):
    #stream = io.BytesIO(bytes(param, 'utf-8'))
    category = unescape(GetParamToken(stream))
    datatype = unescape(GetParamToken(stream))
    name = unescape(GetParamToken(stream)).rstrip('=')
    rec = {
        'name': name, 'comment': '', 'category': category, 'type': datatype,
        'defaultVal': '', 'minVal': '', 'maxVal': '',
    }

    scaled = None
    if datatype in ('int', 'float'):
        datatypestr = datatype
        datatype = {'float': float, 'int': int}.get(datatype)
        val = unescape(GetParamToken(stream))
        unscaled, units, scaled = DecodeUnits(val, datatype)
        if isinstance(unscaled, (str, type(None))): Warn(
            'failed to interpret "%s" as type %s in parameter "%s"' % (val, datatypestr, name))
        rec.update({
            'valstr': val,
            'val': unscaled,
            'units': units,
        })

    elif datatype in ('string', 'variant'):
        val = unescape(GetParamToken(stream))
        rec.update({
            'valstr': val,
            'val': val,
        })

    elif datatype.endswith('list'):
        valtype = datatype[:-4]
        valtypestr = valtype
        valtype = {'float': float, 'int': int, '': str, 'string': str, 'variant': str}.get(valtype, valtype)
        if isinstance(valtype, str): raise DatFileError('Unknown list type "%s"' % datatype)
        numel, labels, labelstr = ParseDim(stream)
        val = []
        for i in range(0, numel):
            t = GetParamToken(stream)
            if not len(t): Warn('not enough values in parameter "%s"' % name)
            val.append(unescape(t))

        valstr = ' '.join([labelstr] + val)
        if valtype == str:
            unscaled = val
            units = [''] * len(val)
        else:
            eachstr = val
            val = [DecodeUnits(x, valtype) for x in eachstr]
            if len(val):
                unscaled, units, scaled = list(zip(*val))[:3]
            else:
                unscaled, units, scaled = [], [], []
            #silence error, it is commonly caused by "auto" parameter
            # for u, v, s in zip(unscaled, val, eachstr):
            #     if isinstance(u, (str, type(None))): Warn(
            #         'failed to interpret "%s" as type %s in parameter "%s"' % (s, valtypestr, name))
        rec.update({
            'valstr': valstr,
            'valtype': valtype,
            'len': numel,
            'val': unscaled,
            'units': units,
        })

    elif datatype.endswith('matrix'):
        valtype = datatype[:-6]
        valtype = {'float': float, 'int': int, '': str, 'string': str, 'variant': str}.get(valtype, valtype)
        if isinstance(valtype, str): raise DatFileError('Unknown matrix type "%s"' % valtype)
        nrows, rowlabels, rowlabelstr = ParseDim(stream)
        ncols, collabels, collabelstr = ParseDim(stream)

        values = []
        for i in range(0, nrows * ncols):
            t = GetParamToken(stream)
            if not len(t): Warn('not enough values in parameter "%s"' % name)
            values.append(unescape(t))

        valstr = ' '.join(filter(len, [rowlabelstr, collabelstr] + values))
        val = []
        for i in range(nrows):
            val.append([])
            for j in range(ncols):
                val[-1].append(values.pop(0))
        rec.update({
            'valstr': valstr,
            'valtype': valtype,
            'val': val,
            'shape': (nrows, ncols),
            'dimlabels': (rowlabels, collabels),
        })

    else:
        Warn("unsupported parameter type %r" % datatype)
        val = unescape(GetParamToken(stream))
        rec.update({
            'valstr': val,
            'val': val,
        })

    vals = []
    t = GetParamToken(stream)
    while len(t):
        if t.find('//') == 0:
            break
        vals.append(unescape(t))
        t = GetParamToken(stream)

    if len(vals): rec['defaultVal'] = vals.pop(0)
    if len(vals): rec['minVal'] = vals.pop(0)
    if len(vals): rec['maxVal'] = vals.pop(0)
    if len(vals): Warn('%d extra value(s) in parameter %s' % (len(vals), name))

    t = t.split('//')
    t = t[-1]
    comment = ' '.join([t, GetLine(stream)])
    rec['comment'] = comment.strip()

    if scaled is None:
        rec['scaled'] = rec['val']
    else:
        rec['scaled'] = scaled
    stream.close()
    return rec


def ParseDim(stream):
    extent = 0
    labels = []
    labelstr = ''

    t = GetParamToken(stream)
    if t.startswith('{'):
        line = GetLine(stream, b'}')
        labelstr = '{ ' + line + ' }'
        stream2 = io.BytesIO(bytes(line, 'utf-8'))
        while True:
            t2 = GetParamToken(stream2)
            if t2 == '': break
            labels.append(unescape(t2))
        stream2.close()
        extent = len(labels)
    else:
        extent = unescape(t)
        labelstr = extent
        extent = int(extent)
        labels = [str(x) for x in range(1, extent + 1)]
    return extent, labels, labelstr


def DecodeUnits(s, datatype=float):
    s = str(s)
    if s.lower().startswith('0x'): return int(s, 16), None, None
    units = ''
    while len(s) and not s[-1] in '0123456789.':
        units = s[-1] + units
        s = s[:-1]
    if len(s) == 0: return None, None, None
    try:
        unscaled = datatype(s)
    except:
        try:
            unscaled = float(s)
        except:
            return s, None, None
    scaled = unscaled * {
        'hz': 1, 'khz': 1000, 'mhz': 1000000,
        'muv': 1, 'mv': 1000, 'v': 1000000,
        'musec': 0.001, 'msec': 1, 'sec': 1000, 'min': 60000,
        'ms': 1, 's': 1000,
    }.get(units.lower(), 1)
    return unscaled, units, scaled
