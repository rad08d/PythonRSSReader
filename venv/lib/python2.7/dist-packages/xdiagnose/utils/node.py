#!/usr/bin/python3

# TODO: Switch to a dict data structure for children
#       See logic in config.py as example.
#       This will give faster lookups using less code.
#       But loses ordering...
#       Ordering could be handled by separate list of keys

class Node(object):
    '''Wraps an object for storing into a tree structure.

    For identification purposes, value needs to either be a
    simple string, a dict with an id field, or an instance
    of a class that has an id attribute.

    The value item must also be convertable to str.
    '''
    def __init__(self, value):
        self.value = value
        self.children = []

    def __str__(self):
        """
        Return a text representation of the node and its children,
        shown in a bulleted outline format.
        """
        text = ''
        for depth, item in self.flatten():
            if depth:
                text += "%s+ %s\n" %('  '*depth, item)
            else:
                text += "%s\n" %(item)
        return text

    def add_child(parent_node, fields):
        """Append a descendants to the parent's child list.

        fields is a lineage of child, grandchild, etc.
        """
        assert(parent_node)
        if len(fields)<=0:
            return

        field = fields[0]
        node = None
        for child in parent_node.children:
            assert(child)
            if child.value == field:
                node = child
        if node is None:
            node = Node(field)
            parent_node.children.append(node)
        if len(fields) > 1:
            node.add_child(fields[1:])

    def find(self, key):
        """
        Locate the item with the value matching the given key.
        If multiple items have the same key, returns the first
        one found.
        """
        if self.value is not None:
            if type(self.value) == type(key):
                if self.value == key:
                    return self
            elif type(self.value) is dict:
                id = self.value.get('id', None)
                if id == key:
                    return self
            elif hasattr(obj, 'id'):
                id = self.value.id
                if id == key:
                    return self

        for node in self.children:
            result = node.find(key)
            if result is not None:
                return result
        return None

    def flatten(self, current_level=0):
        """
        Creates a list representation of the tree.  Each
        element of the list is a tuple of the depth and value.
        """
        items = []
        if self.value:
            items.append((current_level, self.value))
        for node in self.children:
            child_items = node.flatten(current_level+1)
            items.extend(child_items)
        return items


def list_to_tree(items):
    root = Node('root')
    for item in items:
        root.add_child(item.split('.'))
    return root


if __name__ == "__main__":

    def test_create_node():
        node = Node("parent")
        node.add_child("child")
        assert(1 == len(node.children))

    def test_add_child():
        node = Node("parent")
        node.add_child("child")
        assert(1 == len(node.children))

    def test_add_child():
        node = Node("parent")
        node.add_child("a")
        node.add_child("b")
        node.add_child( "c")
        assert(3 == len(node.children))

    def test_create_tree():
        node = Node("parent")
        node.add_child("a")
        node.children[0].add_child("1")
        node.children[0].add_child("2")
        node.add_child("b")
        node.children[1].add_child("1")
        node.children[1].add_child("2")
        assert(2 == len(node.children))

    def test_children_one_level():
        data = [
            'a',
            'b',
            'c',
            ]
        repr = """root
  + a
  + b
  + c
"""
        tree = list_to_tree(data)
        assert(repr == str(tree))

    def test_children_two_levels():
        data = [
            'a.1',
            'a.2',
            'a.3',
            ]
        repr = """root
  + a
    + 1
    + 2
    + 3
"""
        tree = list_to_tree(data)
        assert(repr == str(tree))

    def test_children_three_levels():
        data = [
            'a.1.1',
            'a.2.1',
            'a.3.1',
            ]
        repr = """root
  + a
    + 1
      + 1
    + 2
      + 1
    + 3
      + 1
"""
        tree = list_to_tree(data)
        assert(repr == str(tree))

    def test_children_tree():
        data = [
            'a.1.1',
            'a.1.2',
            'a.2.1',
            ]
        repr = """root
  + a
    + 1
      + 1
      + 2
    + 2
      + 1
"""
        tree = list_to_tree(data)
        assert(repr == str(tree))

    def test_flatten_empty():
        data = []
        tree = list_to_tree(data)
        items = tree.flatten()
        assert((0,'root') == items[0])

    def test_flatten_single():
        data = ['a']
        tree = list_to_tree(data)
        items = tree.flatten()
        assert((1,'a') == items[1])

    def test_flatten_set():
        data = ['a', 'b', 'c']
        tree = list_to_tree(data)
        items = tree.flatten()
        assert(4 == len(items))

    def test_flatten_deep():
        data = ['a.b.c.d.e']
        tree = list_to_tree(data)
        items = tree.flatten()
        assert(6 == len(items))

    def test_flatten_tree():
        data = ['a.1.1',
                'a.1.2',
                'a.2',
                'a.2.1',
                'b.1',
                'c.1.1',
                ]
        tree = list_to_tree(data)
        items = tree.flatten()
        assert(12 == len(items))

    def test_find():
        data = ['a']
        tree = list_to_tree(data)
        node = tree.find('a')
        assert('a' == node.value)

    def test_find_fail():
        data = ['a']
        tree = list_to_tree(data)
        node = tree.find('b')
        assert(None == node)

    def test_find_deep():
        data = ['a.b.c.d.e.f']
        tree = list_to_tree(data)
        node = tree.find('e')
        assert('e' == node.value)

    def test_find_in_set():
        data = ['a.1',
                'a.2',
                'a.3',
                'b.4',
                'b.5',
                'c.6'
                ]
        tree = list_to_tree(data)
        node = tree.find('5')
        assert('5' == node.value)

    def test_find_from_multiple():
        data = ['a.1',
                'a.2',
                'a.3',
                'b.1',
                'b.2',
                'c.1'
                ]
        tree = list_to_tree(data)
        node = tree.find('2')
        assert('2' == node.value)

    test_create_node()
    test_add_child()
    test_add_child()
    test_create_tree()
    test_children_one_level()
    test_children_two_levels()
    test_children_three_levels()
    test_children_tree()
    test_flatten_empty()
    test_flatten_single()
    test_flatten_set()
    test_flatten_deep()
    test_flatten_tree()
    test_find()
    test_find_fail()
    test_find_deep()
    test_find_in_set()
    test_find_from_multiple()

    data = [
        'a.a.a',
        'a.b.a',
        'a.b.b',
        'a.b.c',
        'b.a',
        'c',
        'd',
        'd.a.a',
        ]

    tree = list_to_tree(data)
    print(tree)

    # TODO: Convert back to dotted list
