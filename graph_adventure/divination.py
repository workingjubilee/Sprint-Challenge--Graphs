from numeromancy import Now
from player import Player
from world import World
# import player
# player.travel(move)

'''
The primary goal here is to explore nearby branches and then search down each branch.
Catches: We must be able to identify if we have fully traversed a branch
We must be able to 
'''


class MagicMap:
    def __init__(self, world=None):
        self.world = world
        self.map = {}  # identifies the graph of the rooms
        self.coords = {}  # identifies the coordinates for each room
        self.mapped = set()  # identifies areas which have been explored
        self.leaves = {}  # identifies goalposts: the corners
        self.boughs = {} # identifies the paths to the goalposts

        self.reveal(self.world.rooms)

    def reveal(self, graph):
        # automatically invoked upon casting Magic Map, of course
        # rebuilds graph into a more analyzable form
        self.map = {
            k: {j.id: i[0:1] for (i, j) in v.__dict__.items()
                if i in ['e_to', 's_to', 'w_to', 'n_to']
                and j is not None}
            for (k, v) in graph.items()}
        self.coords = {k: v.getCoords() for (k, v) in graph.items()}

    def _orient(self, room, seed=set()):
        # used to isolate segments
        return [i for i in self.map.get(room) if i not in seed and i not in self.mapped]

    def _bud(self, path, mapping):
        # used by explore, creates joining relationships
        start, end = path[0], path[-1]

        if mapping.get(start):
            mapping[start][end] = path[1:]
        else:
            mapping[start] = { end: path[1:] }

        backtrack = [i for i in path]
        backtrack.reverse()

        if mapping.get(end):
            mapping[end][start] = backtrack[1:]
        else:
            mapping[end] = { start: backtrack[1:] }

    def know_path(self, coming, going, mapping=None):
        # iterates through a defined path to retrieve its directions
        if mapping == None:
            mapping = self.boughs

        sequence = mapping[coming][going]

        previous = coming
        directions = []
        for i in sequence:
            step = self.map[previous][i]
            directions.append(step)
            previous = i

        return directions

    def _rake_leaves(self):
        # initial pass to "compile" leaf nodes into predefined directions
        leaf_pile = {}

        for leaf in self.leaves.keys():
            if leaf not in self.boughs:
                branch = [*self.leaves[leaf]][0]
                back = self.know_path(leaf, branch, self.leaves)
                there = self.know_path(branch, leaf, self.leaves)

                if leaf_pile.get(branch) == None:
                    leaf_pile[branch] = []
                leaf_pile[branch].extend(there + back)

            if leaf in self.boughs and self.leaves.get(leaf).get(leaf):
                loop = self.know_path(leaf, leaf, self.leaves)

                if leaf_pile.get(leaf) == None:
                    leaf_pile[leaf] = []
                leaf_pile[leaf].extend(loop)


        self.leaves = leaf_pile


    def explore(self, root=0, seed=set()):
        # recursively traverses graph in a breadth-first-esque manner
        leaves, stems = self._magic_tree(root, seed)

        for path in leaves:
            self._bud(path, self.leaves)

            self.mapped.update(path)

        for path in stems:
            self._bud(path, self.boughs)

            self.mapped.update(path[:-1])

        horizons = { i[-1] for i in stems }
        for i in horizons:
            self.explore(i)
        

    def _magic_tree(self, root, seed=set()):
        # uses _branch and _grow, depends on Now for control flow
        loops = []
        stems = []
        leaves = []

        branches = self._branch(root)

        while branches:
            branch, switch = branches.pop()

            if switch == Now.CONTINUE:
                branches.append(self._grow(branch))
            elif switch == Now.DONE:
                leaves.append(branch)
            elif bool(switch & Now.LOOP):
                loops.append(branch)
            elif bool(switch & Now.MORE):
                stems.append(branch)

        if len(loops) > 0:
            loop_starts = [i[0] for i in loops]
            loop_ends =  [i[-1] for i in loops]
            if all(loop_starts) == loops[0][0] and loop_starts == loop_ends:
                leaves.append(loops[0])

        return leaves, stems

    def _branch(self, root, seed=set()):
        # helps perform initial operations when joining graph nodes
        branches = []

        for trunk in self._orient(root, seed):
            branching = self._orient(trunk, {root})

            if len(branching) == 1:
                branches.append(
                    ([root, trunk, branching[0]], Now.CONTINUE))
            elif len(branching) > 1:
                branches.append(([root, trunk], Now.MORE))
            else:
                branches.append(([root, trunk], Now.DONE))

        return branches

    def _grow(self, branch):
        # this function grows a "stub" path into a full one
        # base case is more of an error-catch
        if len(branch) < 3:
            return branch, Now.DONE

        # builds its own exploration context
        visited = set(branch[1:])
        path = branch
        room = path[-1]

        branches = self._orient(room, visited)

        while len(branches) == 1:
            branch = [branches[0]]
            path = path + [branches[0]]
            room = path[-1]
            visited.add(room)

            if room == path[0]:
                return path, (Now.DONE | Now.LOOP)

            branches = self._orient(room, visited)

        if len(branches) > 1:
            if path[0] in branches:
                return path, (Now.MORE | Now.LOOP)
            else:
                return path, Now.MORE
        elif len(branches) == 0:
            return path, Now.DONE

        # normally unreachable.
        print("Error:", path, room, visited, branches)

        # so we want to take the starting room
        # branch a function off each one?
        # hmm...

    def guide(self):
        start_at = self.world.startingRoom

        # compress world graph
        self.explore(start_at.id)
        self._rake_leaves()
        self._fold()

        # sets up dry run to verify and trim minor redundancies
        visited_rooms = set()
        stop_at = -1
        # you see in D&D there's this spell called astral projection and...
        projection = Player("Astral Projection", self.world.startingRoom)

        for key, move in enumerate(self.leaves.get(start_at.id)):
            if len(visited_rooms) >= 500:
                stop_at = key # trims some final edges
                break

            projection.travel(move)
            visited_rooms.add(projection.currentRoom)

        return self.leaves.get(start_at.id)[:key]

    def _fold(self):
        # folds "corner" branches into nearby branches for idealized subgraphs
        try:
            folding = {k:v for (k,v) in self.boughs.items() if len(v) == 1}
            if 0 in folding:
                del folding[0] # prevents a KeyError
        except TypeError:
            # this means we messed up
            return
        if len(folding) < 1:
            # base case to cancel infinite recursion when done folding
            return
        
        for corner in folding:
            center = [*self.boughs[corner]][0]
            fold = self.know_path(center, corner)
            tuck = self.know_path(corner, center)

            if self.leaves.get(corner):
                fold.extend(self.leaves[corner])
            fold.extend(tuck)

            if self.leaves.get(center) == None:
                self.leaves[center] = []
            self.leaves[center].extend(fold)

            # cleans up now-"compiled" connections
            try:
                self.boughs.pop(corner)
                self.boughs[center].pop(corner)
                self.leaves.pop(corner)
            except KeyError:
                pass

        self._fold() # recurse to continue folding
