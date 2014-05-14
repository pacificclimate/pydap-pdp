"""
This is the Pydap data model, an implementation of the Data Access Protocol 
data model written in Python. 

The model is composed of a base object which represents data, the `BaseType`, 
and by objects which can hold other objects, all derived from `StructureType`.
Here's a simple example of a `BaseType` variable::

    >>> import numpy as np
    >>> foo = BaseType('foo', np.arange(4, dtype='i'))
    >>> print foo[-2:]
    [2 3]
    >>> print foo.dtype
    int32
    >>> print foo.shape
    (4,)
    >>> for record in foo:
    ...     print record
    0
    1
    2
    3
    
The `BaseType` is simply a thin wrapper over Numpy arrays, implementing the 
`dtype` and `shape` attributes, and the sequence and iterable protocols. Why not 
use Numpy arrays directly then? First, `BaseType` can have additional metadata
added to them; this include names for its dimensions and also arbitrary 
attributes::

    >>> print foo.attributes
    {}
    >>> foo.attributes['units'] = 'm/s'
    >>> print foo.units
    m/s

    >>> print foo.dimensions
    ()
    >>> foo.dimensions = ('time',)
    
Second, `BaseType` can hold data objects other than Numpy arrays. There are more
complex data objects, like `pydap.proxy.ArrayProxy`, which acts as a transparent 
proxy to a remote dataset, exposing it through the same interface.

Now that we have some data, we can organize it using containers::

    >>> dataset = DatasetType('baz')
    >>> dataset['s'] = StructureType('s')
    >>> dataset['s']['foo'] = foo
    
`StructureType` and `DatasetType` are very similar; the only difference is that
`DatasetType` should be used as the root container for a dataset. They behave
like ordered Python dictionaries::
    
    >>> print dataset.s.keys()
    ['foo']
    
A `GridType` is a special container where the first child should be an 
n-dimensional `BaseType`. This children should be followed by `n` additional
vector `BaseType` objects, each one describing one of the axis of the variable::

    >>> rain = GridType('rain')
    >>> rain['rain'] = BaseType('rain', np.arange(6).reshape(2, 3), dimensions=('y', 'x'))
    >>> rain['x'] = BaseType('x', np.arange(3), units='degrees_east')
    >>> rain['y'] = BaseType('y', np.arange(2), units='degrees_north')
    >>> print rain.array  #doctest: +ELLIPSIS
    <__main__.BaseType object at ...>
    >>> print rain.maps  #doctest: +ELLIPSIS
    OrderedDict([('x', <__main__.BaseType object at ...>), ('y', <__main__.BaseType object at ...>)])
    
There a last special container called `SequenceType`. This data structure is 
analogous to a series of records (or rows), with one column for each of its
children::

    >>> cast = SequenceType('cast')
    >>> cast['depth'] = BaseType('depth', positive='down', units='m')
    >>> cast['temperature'] = BaseType('temperature', units='K')
    >>> cast['salinity'] = BaseType('salinity', units='psu')
    >>> cast['id'] = BaseType('id')
    >>> cast.data = np.array([(10., 17., 35., '1'), (20., 15., 35., '2')],
    ...     dtype=np.dtype([('depth', np.float32), ('temperature', np.float32),
    ...     ('salinity', np.float32), ('id', np.dtype('|S1'))]))
    
Note that the data in this case is attributed to the `SequenceType`, and is 
composed of a series of values for each of the children.  Pydap `SequenceType` 
obects are very flexible. Data can be accessed by iterating over the object::

    >>> for record in cast:
    ...     print record
    (10.0, 17.0, 35.0, '1')
    (20.0, 15.0, 35.0, '2')

It is possible to select only a few variables::

    >>> for record in cast['salinity', 'depth']:
    ...     print record
    (35.0, 10.0)
    (35.0, 20.0)

    >>> print cast['temperature'].dtype
    float32
    >>> print cast['temperature'].shape
    (2,)
    >>> for record in cast['temperature'][-1:]:
    ...     print record
    15.0

    >>> for record in cast[ cast['temperature'] < 16 ]:
    ...     print record
    (20.0, 15.0, 35.0, '2')

"""

import operator
import itertools
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import numpy as np

from pydap.lib import quote


__all__ = ['DapType', 'BaseType', 'StructureType', 'DatasetType', 'SequenceType', 'GridType']


class DapType(object):
    """
    The common Opendap type.
    
    This is a base class, defining common methods and attributes for all other 
    classes in the data model.
    
    """
    def __init__(self, name, attributes=None, **kwargs):
        self.name = quote(name)
        self.attributes = attributes or {}
        self.attributes.update(kwargs)
        
        # Set the id to the name.
        self._id = self.name

    def __repr__(self):
        return 'DapType(%s)' % ', '.join(map(repr, [self.name, self.attributes]))
        
    # The id.
    def _set_id(self, id):
        self._id = id
            
        # Update children id.
        for child in self.children():
            child.id = '%s.%s' % (id, child.name)
            
    def _get_id(self):
        return self._id
        
    id = property(_get_id, _set_id)
    
    def __getattr__(self, attr):
        """
        Attribute shortcut.
        
        Data classes have their attributes stored in the `attributes` attribute,
        a dictionary. For convenience, access to attributes can be shortcut by 
        accessing the attributes directly::
        
            >>> var = DapType('var')
            >>> var.attributes['foo'] = 'bar'
            >>> print var.foo
            bar
            
        """
        try:
            return self.attributes[attr]
        except (KeyError, TypeError):
            raise AttributeError(
                "'%s' object has no attribute '%s'"
                % (self.__class__, attr))
        
    def children(self):
        """
        Iterate over children.
        
        """
        return ()
        

class BaseType(DapType):
    """
    A thin wrapper over Numpy arrays.
    
    """
    def __init__(self, name, data=None, dimensions=None, attributes=None, **kwargs):
        DapType.__init__(self, name, attributes, **kwargs)
        self.data = data
        self.dimensions = dimensions or ()
        
    def __repr__(self):
        return '<%s with data %s>' % (self.__class__.__name__, repr(self.data))
        
    @property
    def dtype(self):
        return self.data.dtype
        
    @property
    def shape(self):
        return self.data.shape

    def clone(self):
        """
        A lightweight copy of the variable.
        
        This will return a new object, with a copy of the attributes, dimensions,
        same name, and a view of the data.
        
        """
        out = self.__class__(self.name, self.data, self.dimensions[:], self.attributes.copy())
        out.id = self.id
        return out

    # Comparisons are passed to the data.
    def __eq__(self, other): return self.data == other
    def __ne__(self, other): return self.data != other
    def __ge__(self, other): return self.data >= other
    def __le__(self, other): return self.data <= other
    def __gt__(self, other): return self.data > other
    def __lt__(self, other): return self.data < other
    
    # Implement the sequence and iter protocols.
    def __getitem__(self, index): return self.data[index]
    def __len__(self): return self.shape[0]
    def __iter__(self): return iter(self.data)


class StructureType(DapType):
    def __init__(self, name, attributes=None, **kwargs):
        DapType.__init__(self, name, attributes, **kwargs)

        # emulate a simple ordered dict
        self._keys = []
        self._dict = {}
        
    def __repr__(self):
        return '<%s with children %s>' % (self.__class__.__name__, 
            ', '.join(map(repr, self.keys())))

    def __contains__(self, child):
        return self._dict.__contains__(child)
        
    def __getattr__(self, attr):
        """
        Lazy shortcut for accessing children.
        
        """
        try:
            return self[attr]
        except:
            return DapType.__getattr__(self, attr)
            
    def __iter__(self):
        for key in self._keys:
            yield self._dict[key]
    children = __iter__
    
    def __setitem__(self, key, item):
        key = quote(key)
        if key != item.name:
            raise KeyError('Key "%s" is different from variable name "%s"!' %
                (key, item.name))

        if key in self._keys:
            self._keys.pop(self._keys.index(key))
        self._keys.append(key)
        self._dict[key] = item
        
        # Set item id.
        item.id = '%s.%s' % (self.id, item.name)

    def __getitem__(self, key):
        return self._dict[key]

    def __delitem__(self, key):
        self._dict.__delitem__(key)
        self._keys.remove(key)

    def keys(self):
        return self._keys[:]

    def _get_data(self):
        return [var.data for var in self.children()]
    def _set_data(self, data):
        for col, var in zip(data, self.children()):
            var.data = col
    data = property(_get_data, _set_data)
    
    def clone(self):
        out = self.__class__(self.name, self.attributes.copy())
        out.id = self.id
        
        # Clone children too.
        for child in self.children():
            out[child.name] = child.clone()
            
        return out
        
        
class DatasetType(StructureType):
    def __setitem__(self, key, item):
        if key != item.name:
            raise KeyError('Key "%s" is different from variable name "%s"!' % 
                (key, item.name))
        StructureType.__setitem__(self, key, item)
        
        # The dataset name does not goes into the children ids.
        item.id = item.name
        
    def _set_id(self, id):
        """
        The method must be implemented so that the dataset name is not included
        in the children ids.
        
        """
        self._id = id
        
        for child in self.children():
            child.id = child.name
            
            
class SequenceType(StructureType):
    """
    A container that stores data in a Numpy array.

    Here's a standard dataset for testing sequential data:

        >>> data = np.array([
        ... (10, 15.2, 'Diamond_St'), 
        ... (11, 13.1, 'Blacktail_Loop'),
        ... (12, 13.3, 'Platinum_St'),
        ... (13, 12.1, 'Kodiak_Trail')],
        ... dtype=np.dtype([
        ... ('index', np.int32), ('temperature', np.float32),
        ... ('site', np.dtype('|S14'))]))

    Iteraring over the sequence returns data:

        >>> seq = SequenceType('example')
        >>> seq['index'] = BaseType('index')
        >>> seq['temperature'] = BaseType('temperature')
        >>> seq['site'] = BaseType('site')
        >>> seq.data = data  # XXX UGLY TODO

        >>> for line in seq:
        ...     print line
        (10, 15.199999809265137, 'Diamond_St')
        (11, 13.100000381469727, 'Blacktail_Loop')
        (12, 13.300000190734863, 'Platinum_St')
        (13, 12.100000381469727, 'Kodiak_Trail')

    The order of the variables can be changed:

        >>> for line in seq['temperature', 'site', 'index']:
        ...     print line
        (15.199999809265137, 'Diamond_St', 10)
        (13.100000381469727, 'Blacktail_Loop', 11)
        (13.300000190734863, 'Platinum_St', 12)
        (12.100000381469727, 'Kodiak_Trail', 13)

    We can iterate over children:

        >>> for line in seq['temperature']:
        ...     print line
        15.2
        13.1
        13.3
        12.1

    We can filter the data:

        >>> for line in seq[ seq.index > 10 ]:
        ...     print line
        (11, 13.100000381469727, 'Blacktail_Loop')
        (12, 13.300000190734863, 'Platinum_St')
        (13, 12.100000381469727, 'Kodiak_Trail')

        >>> for line in seq[ seq.index > 10 ]['site']:
        ...     print line
        Blacktail_Loop
        Platinum_St
        Kodiak_Trail

        >>> for line in seq['site', 'temperature'][ seq.index > 10 ]:
        ...     print line
        ('Blacktail_Loop', 13.100000381469727)
        ('Platinum_St', 13.300000190734863)
        ('Kodiak_Trail', 12.100000381469727)

    Or slice it:

        >>> for line in seq[::2]:
        ...     print line
        (10, 15.199999809265137, 'Diamond_St')
        (12, 13.300000190734863, 'Platinum_St')

        >>> for line in seq[ seq.index > 10 ][::2]['site']:
        ...     print line
        Blacktail_Loop
        Kodiak_Trail

        >>> for line in seq[ seq.index > 10 ]['site'][::2]:
        ...     print line
        Blacktail_Loop
        Kodiak_Trail

    """

    def __init__(self, name, data=None, attributes=None, **kwargs):
        StructureType.__init__(self, name, attributes, **kwargs)
        self._data = data
        
    def _set_data(self, data):
        self._data = data
        for child in self.children():
            tokens = child.id[len(self.id)+1:].split('.')
            child.data = reduce(operator.getitem, [data] + tokens)

    def _get_data(self):
        return self._data

    data = property(_get_data, _set_data)
        
    def __setitem__(self, key, item):
        StructureType.__setitem__(self, key, item)
        
    def __len__(self): return len(self.data)
    def __iter__(self): return iter(self.data)

    def __getitem__(self, key):
        # If key is a string, return child with the corresponding data.
        if isinstance(key, basestring):
            return StructureType.__getitem__(self, key)
            
        # If it's a tuple, return a new `SequenceType` with selected children.
        elif isinstance(key, tuple):
            out = SequenceType(self.name, self.data, self.attributes.copy())
            for name in key:
                out[name] = StructureType.__getitem__(self, name).clone()
            out.data = self.data[list(key)]
            return out
            
        # Else return a new `SequenceType` with the data sliced.
        else:
            out = self.clone()
            out.data = self.data[key]
            return out

    def clone(self):
        out = self.__class__(self.name, self.data, self.attributes.copy())
        out.id = self.id
        
        # Clone children too.
        for child in self.children():
            out[child.name] = child.clone()

        return out


class GridType(StructureType):
    def __repr__(self):
        return '<%s with array %s and maps %s>' % (self.__class__.__name__, 
            repr(self.keys()[0]), ', '.join(map(repr, self.keys()[1:])))

    def __getitem__(self, key):
        # Return a child.
        if isinstance(key, basestring):
            return StructureType.__getitem__(self, key)

        # Return a new `GridType` with part of the data.
        else:

            if not isinstance(key, tuple):
                key = (key,)

            out = self.clone()
            for var, slice_ in zip(out.children(), [key] + list(key)):
                var.data = self[var.name][slice_]
            return out

    @property
    def array(self):
        return self[self.keys()[0]]

    @property
    def maps(self):
        return OrderedDict((k, self[k]) for k in self.keys()[1:])

    @property
    def dimensions(self):
        return tuple(self.keys()[1:])


def pack_rows(data, level):
    """
    Packs data from separate variables.

    This function is used to pack columnar data into a sequence of records::

        >>> a = [1, 2, 3]
        >>> b = [10, 20, 30]
        >>> c = [1, 1, 1]
        >>> for record in pack_rows([a, b, c], 1):
        ...     print record
        ...
        (1, 10, 1)
        (2, 20, 1)
        (3, 30, 1)

    "This is trival!", you might say. But what if we have nested containers? It
    works too::

        >>> d = [ ['a', 'b', 'c'], ['d'], ['e', 'f'] ]
        >>> e = [ [1, 2, 3], [4], [5, 6] ]
        >>> for record in pack_rows([d, e], 2):
        ...     print record
        ...
        [('a', 1), ('b', 2), ('c', 3)]
        [('d', 4)]
        [('e', 5), ('f', 6)]

    """
    if level == 0:
        return data
    else:
        return [ pack_rows(value, level-1) for value in zip(*data) ]
        
        
def unpack_rows(data, level):
    """
    Unpack container data into columns.

    Suppose we have a list of records, one for each of 3 variables, this
    function will unpack the data into 3 columns::

        >>> data = [(1, 10, 1), (2, 20, 1)]
        >>> print unpack_rows(data, 1)
        [(1, 2), (10, 20), (1, 1)]

    It works with nested data too::

        >>> data = [
        ...     [('a', 1), ('b', 2), ('c', 3)],
        ...     [('d', 4)],
        ...     [('e', 5), ('f', 6)] ]
        >>> print unpack_rows(data, 2)
        [(('a', 'b', 'c'), ('d',), ('e', 'f')), ((1, 2, 3), (4,), (5, 6))]

    """
    if level == 0:
        return data
    else:
        return zip(*[ unpack_rows(value, level-1) for value in data ])
        

def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()
