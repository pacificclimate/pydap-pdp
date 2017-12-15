import re
from urllib import quote, unquote


def parse_projection(input):
    """
    Split a projection into items, taking into account server-side functions,
    and parse slices.

    """
    def tokenize(input):
        start = pos = count = 0
        for char in input:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
            elif char == ',' and count == 0:
                yield input[start:pos]
                start = pos+1
            pos += 1
        yield input[start:]

    def parse(token):
        if '(' not in token:
            token = token.split('.')
            token = [ re.match('(.*?)(\[.*\])?$', part).groups() 
                for part in token ]
            token = [ (quote(name), parse_hyperslab(slice_ or '')) 
                for (name, slice_) in token ]
        return token

    return map(parse, tokenize(input))


def parse_ce(query_string):
    """
    Extract the projection and selection from the QUERY_STRING.

        >>> parse_ce('a,b[0:2:9],c&a>1&b<2')
        ([[('a', ())], [('b', (slice(0, 10, 2),))], [('c', ())]], ['a>1', 'b<2'])
        >>> parse_ce('a>1&b<2')
        ([], ['a>1', 'b<2'])

    This function can also handle function calls in the URL, according to the
    DAP specification:

        >>> parse_ce('time&bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)')
        ([[('time', ())]], ['bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)'])
        >>> parse_ce('time,bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)')
        ([[('time', ())], 'bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z04JAN1970)'], [])
        >>> parse_ce('mean(g,0)')
        (['mean(g,0)'], [])
        >>> parse_ce('mean(mean(g.a,1),0)')
        (['mean(mean(g.a,1),0)'], [])

    """
    tokens = [ token for token in unquote(query_string).split('&') if token ]
    if not tokens:
        projection = []
        selection = []
    elif re.search('<=|>=|!=|=~|>|<|=', tokens[0]):
        projection = []
        selection = tokens
    else:
        projection = parse_projection(tokens[0])
        selection = tokens[1:]

    return projection, selection


def parse_hyperslab(hyperslab):
    """
    Parse a hyperslab into a Python tuple of slice objects.
    OpenDAP subsetting indices are different than NumPy's,
    See https://goo.gl/swVCdN

    >>> parse_hyperslab("[36]")
    (slice(36, 37, None))
    >>> parse_hyperslab("[1:2]")
    (slice(1, 3, None))
    >>> parse_hyperslab("[1:2:6][][3:5:]")
    (slice(1, 7, 2), slice(None, None, None), slice(3, None, 5))
    """

    dimensions = []
    slices = []
    to_split = hyperslab

    while to_split:
        rbracket = to_split.find(']') + 1
        dimensions.append(to_split[:rbracket])
        to_split = to_split[rbracket:]

    for dim in dimensions:
        dim = dim.strip("[]")
        tokens = dim.split(":")

        start = stop = step = None

        if len(tokens) == 1:
            #no colon in this chunk
            #so either the original dimension was [], indicating a full slice,
            #(in which case start, stop, and step should all be None)
            #or a number like [57], indicating a single index
            if tokens[0]:
                start = int(tokens[0])
                stop = start + 1
        elif len(tokens) == 2:
            #either [start :] or [start:last]
            start = int(tokens[0])
            stop = int(tokens[1]) + 1 if tokens[1] else None
        elif len(tokens) == 3:
            #either [start: step :] or [start : step : last]
            start = int(tokens[0])
            step = int(tokens[1])
            stop = int(tokens[2]) + 1 if tokens[2] else None

        slices.append(slice(start, stop, step))

    return tuple(slices)

class SimpleParser(object):
    """
    A very simple parser.

    """
    def __init__(self, input, flags=0):
        self.buffer = input
        self.flags = flags

    def peek(self, regexp):
        p = re.compile(regexp, self.flags)
        m = p.match(self.buffer)
        if m: 
            token = m.group()
        else:
            token = ''
        return token

    def consume(self, regexp):
        p = re.compile(regexp, self.flags)
        m = p.match(self.buffer)
        if m: 
            token = m.group()
            self.buffer = self.buffer[len(token):]
        else:
            raise Exception("Unable to parse token: %s" % self.buffer[:10])
        return token

    def __nonzero__(self):
        return len(self.buffer)


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()
