#!/usr/bin/env python

import argparse
import re
import subprocess, sys, os
from pythonds import Queue, Graph, Vertex

vertices = []
consumes = Graph()
is_consumed = Graph()
blacklisted_modules_id = []

class MyVertex(Vertex):
    WHITE = 0
    GRAY = 1
    BLACK = 2
    def __init__(self,num):
        self.color = MyVertex.WHITE
        super().__init__(num)

def bfs(graph, start, debug=False):
      """
      Breadth First Search (BFS)
       Given a node in a graph, BFS will find all nodes connected to this
      node. The distance between nodes is measured in HOPS. It will find
      all nodes at distance 'k' before finding any nodes at a further
      distance. It will return the full list of connected nodes.
       PseudoCode:
       BFS(G,s)
       for each vertex u in V[G] - {s} do
        state[u] = WHITE
        predecessor[u] = nil
      state[s] = GRAY
      predecessor[s] = nil
      QUEUE = {s}
      while QUEUE != 0 do
        u = dequeue[Q]
        process vertex u as desired
        for each v in Adjacent[u] do
          process edge (u,v) as desired (e.g. distance[v] = distance[u] + 1)
          if state[v] = WHITE then
            state[v] = GRAY
            predecessor[v] = u
            enqueue[Q,v]
        state[u] = BLACK
      """
      result = []
      for v in graph.getVertices():
          a_vertex = graph.getVertex(v)
          a_vertex.__classname__ = 'MyVertex'
          a_vertex.setColor(MyVertex.WHITE)
          a_vertex.setDistance(0)
          a_vertex.setPred(None)

      start.setDistance(0)
      start.setPred(None)
      vertex_queue = Queue()
      vertex_queue.enqueue(start)
      while (vertex_queue.size() > 0):
          current_vertex = vertex_queue.dequeue()
          result.append(current_vertex)
          if debug:
              print(current_vertex)
          for v in current_vertex.getConnections():
              if v.getColor() == MyVertex.WHITE:
                  v.setColor(MyVertex.GRAY)
                  v.setDistance(current_vertex.getDistance() + 1)
                  v.setPred(current_vertex)
                  vertex_queue.enqueue(v)
          current_vertex.setColor(MyVertex.BLACK)
      return result

def createGraph(args):
    blacklist_modules = []
    if args.exclude_from_nodes:
        blacklist_modules.extend(args.exclude_from_nodes)
    if args.exclude_from_files:
        with open(args.exclude_from_files, 'r') as f:
            lines = [line.rstrip() for line in f]
        blacklist_modules.extend(lines)

    with open('%s' % args.filename, 'r') as f:
        for line in f:
            m = re.match('(\d+).*label=(\w+),.*tooltip=(\w+)', line)
            if m:
                vertices.append(Vertex(int(m.group(1))))
                vertices[-1].label = m.group(2)
                vertices[-1].tooltip = m.group(3)
                vertices[-1].linecolor = 'black'
                if m.group(2) in blacklist_modules:
                    blacklisted_modules_id.append(int(m.group(1)))
                    vertices[-1].linecolor = 'red'
            m = re.match('(\d+) -> (\d+);', line)
            if m:
                if not int(m.group(1)) in blacklisted_modules_id:
                    consumes.addEdge(int(m.group(1)), int(m.group(2)))
                if not int(m.group(2)) in blacklisted_modules_id:
                    is_consumed.addEdge(int(m.group(2)), int(m.group(1)))

def toDotOutput(args, graph, append):
    root_label = args.label
    outputFormat = args.output
    maxNodes = args.maxNodes
    root_nodes = [v for v in vertices if v.label == root_label]
    assert(len(root_nodes)<=1)
    print("Generating the '%s' graph..." % append)
    nodes = bfs(graph, graph.getVertex(root_nodes[0].getId()))
    filename = args.outputfile
    if filename == '':
        filename = root_label
    with open('%s_%s.gv' % (filename, append), 'w') as output:
        used_nodes = []
        output.write('digraph RECO { graph [label = "%s", labelloc=top];\n' % root_label)
        for n in nodes:
            if (maxNodes is not None and len(used_nodes) >= int(maxNodes)):
                continue
            index = n.getId()
            if index not in used_nodes:
                used_nodes.append(index)
                output.write('%d[label=%s, tooltip=%s, color=%s];\n' % (index, vertices[index].label, vertices[index].tooltip, vertices[index].linecolor))
            for child in n.getConnections():
                if child.getId() not in used_nodes:
                    used_nodes.append(child.getId())
                    output.write('%d[label="%s\\n%s", tooltip=%s, color=%s, shape=box];\n' % (child.getId(),
                                                                  vertices[child.getId()].label,
                                                                  vertices[child.getId()].tooltip,
                                                                  vertices[child.getId()].tooltip,
                                                                  vertices[child.getId()].linecolor))
                output.write('%d -> %d;\n' % (n.getId(), child.getId()))

        output.write('}\n')
        print("Graph processed.")
        print("Analyzed %d nodes." % len(used_nodes))
    try:
        f = open(os.devnull, 'w')
        _ = subprocess.check_call(
                ['dot',
                 '-Grankdir=LR',
                 '-Gmindist=4.0',
                 '-Gsplines=ortho',
                 '-v',
                 '-T{outputFormat}'.format(outputFormat=outputFormat),
                 '{filename}_{append}.gv'.format(filename=filename, append=append),
                 '-o',
                 '{filename}_{append}.{outputFormat}'.format(filename=filename, outputFormat=outputFormat, append=append)
                 ], stdout=f, stderr=f)
    except subprocess.CalledProcessError as e:
        print("Return value:{}".format(e.returcode))
        print("Output: {}".format(e.output))
        sys.exit(1)
    print("Done.")

def searchAndPrintNode(args):
    createGraph(args)
    toDotOutput(args, consumes, 'consumes')
    toDotOutput(args, is_consumed, 'is_consumed_by')

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Explore CMSSW FWK dependency graph.')
  parser.add_argument('-f', '--filename',
                     default = None,
                     help = 'Dependency file to use to extract information.',
                     type = str,
                     required=True)
  parser.add_argument('-l', '--label',
                     default = '',
                     help = 'Label of the python module to use as the main vertex of the Graph.',
                     type = str,
                     required=False)
  parser.add_argument('-o', '--output',
                     default = 'pdf',
                     help = 'Output extension of the generated plots.',
                     type = str,
                     required=False)
  parser.add_argument('-O', '--outputfile',
                     default = '',
                     help = 'Output filename, w/o extension, to be used. If none given, use the label of the root module.',
                     type = str,
                     required=False)
  parser.add_argument('-m', '--maxNodes',
                     default = None,
                     help = 'Maximum number of nodes to plot (using BFS exploration of the graph).',
                     type = str,
                     required=False)
  parser.add_argument('--exclude_from_nodes',
                     nargs='*',
                     default = '',
                     help = 'List of python labels starting from which nodes will be pruned while exploring the graph.',
                     required=False,
                     type=str)
  parser.add_argument('--exclude_from_files',
                     default = '',
                     help = 'Text file that contains the list of python labels starting from which nodes will be pruned while exploring the graph. One module per line.',
                     required=False,
                     type=str)
  args = parser.parse_args()
  print(args)
  searchAndPrintNode(args)
