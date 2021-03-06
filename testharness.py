# import matplotlib.pyplot as plt
import os 
import argparse
import subprocess
import json
import re
import matplotlib.pyplot as plt
from string import Template
from enum import Enum
import time
import math

class Fields(str, Enum):
  TIME = 'time'
  SIZE = 'size'
  CALLS = 'calls'
  FLIPS = 'flips'
  PARAMS = 'params'
  DISTINCT = 'distinct'

  def __str__(self):
    return self.value

class Modes(str, Enum):
  NOOPT = 'no opts'
  DET = 'det + be'
  FH = 'fh + det + be'
  FHCT = 'fh + ct + det + be'
  SBK = 'sbk + det + be'
  SBKFH = 'sbk + fh + det + be'
  SBKFHCT = 'sbk + fh + ct + det + be'

  EA = 'ea'
  EADET = 'ea + det + be'
  EAFH = 'ea + fh + det + be'
  EAFHCT = 'ea + fh + ct + det + be'
  EASBK = 'ea + sbk + det + be'
  EASBKFH = 'eg + sbk + fh + det + be'
  EASBKFHCT = 'eg + sbk + fh + ct + det + be'

  def __str__(self):
    return self.name

  @staticmethod
  def from_string(s):
    try:
      return Modes[s]
    except KeyError:
      raise ValueError()

  @staticmethod
  def to_column(m):
    mapping = {
      Modes.NOOPT: 'No Opt',
      Modes.DET: 'Det',
      Modes.FH: 'FH',
      Modes.FHCT: 'FHCT',
      Modes.SBK: 'SBK',
      Modes.SBKFH: 'SBK+FH',
      Modes.SBKFHCT: 'SBK+FHCT',
      Modes.EA: 'Ea',
      Modes.EADET: 'Ea+Det',
      Modes.EAFH: 'Ea+FH',
      Modes.EAFHCT: 'Ea+FHCT',
      Modes.EASBK: 'Ea+SBK',
      Modes.EASBKFH: 'Ea+SBK+FH',
      Modes.EASBKFHCT: 'Ea+SBK+FHCT'
    }
    
    return mapping[m]

def get_mode_cmd(mode):
  if mode == Modes.NOOPT:
    return []
  if mode == Modes.DET:
    return ['-determinism']
  if mode == Modes.FH:
    return ['-determinism', '-local-hoisting', '-branch-elimination']
  if mode == Modes.FHCT:
    return ['-determinism', '-global-hoisting', '-branch-elimination']
  if mode == Modes.SBK:
    return ['-determinism', '-sbk-encoding', '-branch-elimination']
  if mode == Modes.SBKFH:
    return ['-determinism', '-local-hoisting', '-sbk-encoding', '-branch-elimination']
  if mode == Modes.SBKFHCT:
    return ['-determinism', '-global-hoisting', '-sbk-encoding', '-branch-elimination']
  if mode == Modes.EA:
    return ['-eager-eval']
  if mode == Modes.EADET:
    return ['-eager-eval', '-determinism', '-branch-elimination']
  if mode == Modes.EAFH:
    return ['-eager-eval', '-local-hoisting', '-determinism', '-branch-elimination']
  if mode == Modes.EAFHCT:
    return ['-eager-eval', '-global-hoisting', '-determinism', '-branch-elimination']
  if mode == Modes.EASBK:
    return ['-eager-eval', '-sbk-encoding', '-determinism', '-branch-elimination']
  if mode == Modes.EASBKFH:
    return ['-eager-eval', '-sbk-encoding', '-local-hoisting', '-determinism', '-branch-elimination']
  if mode == Modes.EASBKFHCT:
    return ['-eager-eval', '-sbk-encoding', '-global-hoisting', '-determinism', '-branch-elimination']
  
  return None

def run(file, dice_path, timeout, fields, modes, results):
  print('========================================')

  print('File:', file)

  if Fields.TIME in fields:
    print('Measuring time elapsed...')
    for mode in modes:
      cmd = get_mode_cmd(mode)
      if cmd is None:
        print('UNKNOWN MODE')
        continue

      print('Mode:', mode)
      
      if results[Fields.TIME][mode] is not None and results[Fields.TIME][mode] != -1:
        print('Skip')
        continue

      try:
        t1 = time.time()
        p = subprocess.Popen([dice_path, file, '-skip-table', '-show-time'] + cmd, 
          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(timeout=timeout)
        t2 = time.time()
        results[Fields.TIME][mode] = round(t2 - t1, 4)

      # try:
      #   p = subprocess.Popen([dice_path, file, '-skip-table', '-show-time'] + cmd, 
      #     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      #   out, err = p.communicate(timeout=timeout)
      #   output = out.decode('utf-8')
      #   time_pattern = re.compile('================\[ Compilation Time Elapsed \]================\s(\d+.?\d*)')
        
      #   time_matches = time_pattern.search(output)

      #   if time_matches:
      #     if not Fields.TIME in results:
      #       results[Fields.TIME] = {}
      #     results[Fields.TIME][mode] = float(time_matches.group(1))

      except subprocess.TimeoutExpired:
        print('TIMEOUT')
        p.terminate()

    print()
  
  if Fields.SIZE in fields or Fields.CALLS in fields or Fields.FLIPS in fields \
    or Fields.PARAMS in fields or Fields.DISTINCT in fields:
    print('Measuring BDD size, number of recursive calls, and/or number of calls...')
    cmd = [dice_path, file, '-skip-table']
    if Fields.SIZE in fields:
      cmd.append('-show-size')
    if Fields.CALLS in fields:
      cmd.append('-num-recursive-calls')

    if not Fields.SIZE in fields and not Fields.CALLS in fields:
      cmd.append('-no-compile')
    
    if Fields.FLIPS in fields:
      cmd.append('-show-flip-count')
    if Fields.PARAMS in fields:
      cmd.append('-show-params')

    for mode in modes:
      mode_cmd = get_mode_cmd(mode)
      if mode_cmd is None:
        print('UNKNOWN MODE')
        continue

      print('Mode:', mode)

      skip = False
      for f in fields:
        if f != Fields.TIME and f in results \
          and mode in results[f] \
          and results[f][mode] is not None \
          and results[f][mode] != -1:
          skip = True
          break
      if skip:
        print('Skip')
        continue

      try:
        p = subprocess.Popen(cmd + mode_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(timeout=timeout)
        output = out.decode('utf-8')
        call_pattern = re.compile('================\[ Number of recursive calls \]================\s(\d+.?\d*)')
        size_pattern = re.compile('================\[ Final compiled BDD size \]================\s(\d+.?\d*)')
        flip_pattern = re.compile('================\[ Number of flips \]================\s(\d+.?\d*)')
        param_pattern = re.compile('================\[ Number of Parameters \]================\s(\d+.?\d*)')
        distinct_pattern = re.compile('================\[ Number of Distinct Parameters \]================\s(\d+.?\d*)')
        
        call_matches = call_pattern.search(output)
        size_matches = size_pattern.search(output)
        flip_matches = flip_pattern.search(output)
        param_matches = param_pattern.search(output)
        distinct_matches = distinct_pattern.search(output)

        if call_matches:
          if not Fields.CALLS in results:
            results[Fields.CALLS] = {}
          results[Fields.CALLS][mode] = int(float(call_matches.group(1)))
        
        if size_matches:
          if not Fields.SIZE in results:
            results[Fields.SIZE] = {}
          results[Fields.SIZE][mode] = int(float(size_matches.group(1)))

        if flip_matches:
          if not Fields.FLIPS in results:
            results[Fields.FLIPS] = {}
          results[Fields.FLIPS][mode] = int(float(flip_matches.group(1)))

        if param_matches:
          if not Fields.PARAMS in results:
            results[Fields.PARAMS] = {}
          results[Fields.PARAMS][mode] = int(float(param_matches.group(1)))

        if distinct_matches:
          if not Fields.DISTINCT in results:
            results[Fields.DISTINCT] = {}
          results[Fields.DISTINCT][mode] = int(float(distinct_matches.group(1)))

        if not call_matches and not size_matches and not flip_matches and not param_matches:
          if not Fields.CALLS in results:
            results[Fields.CALLS] = {}
          if not Fields.SIZE in results:
            results[Fields.SIZE] = {}
          if not Fields.FLIPS in results:
            results[Fields.FLIPS] = {}
          if not Fields.PARAMS in results:
            results[Fields.PARAMS] = {}
          if not Fields.DISTINCT in results:
            results[Fields.DISTINCT] = {}
          results[Fields.SIZE][mode] = -1
          results[Fields.CALLS][mode] = -1
          results[Fields.FLIPS][mode] = -1
          results[Fields.PARAMS][mode] = -1
          results[Fields.DISTINCT][mode] = -1
          print('ERROR:')
          print(output)

      except subprocess.TimeoutExpired:
        print('TIMEOUT')
        p.terminate()

    print()

  return results

def problog(file, timeout):
  print('========================================')

  print('File:', file)

  print('Measuring time elapsed...')
  try:
    t1 = time.time()
    p = subprocess.Popen(['problog', file], 
      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate(timeout=timeout)
    t2 = time.time()
    result = round(t2 - t1, 4)
    print()
    return result

  except subprocess.TimeoutExpired:
    print('TIMEOUT')
    p.terminate()
    print()
    return None

def cnf(file, dice_path, timeout, results):
  print('========================================')

  print('File:', file)

  modes = [Modes.DET, Modes.FH]

  print('Measuring BDD size, number of recursive calls, and/or number of calls...')
  cmd = [dice_path, file, '-cnf', '-show-cnf-decisions', '-fc-timeout', '5']
  for mode in modes:
    if Fields.SIZE in results:
      if results[Fields.SIZE][mode] is not None and results[Fields.SIZE][mode] != -1:
        print('Skip')
        continue

    mode_cmd = get_mode_cmd(mode)
    if mode_cmd is None:
      print('UNKNOWN MODE')
      continue

    print('Mode:', mode)

    try:
      p = subprocess.Popen(cmd + mode_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      out, err = p.communicate(timeout=timeout)
      output = out.decode('utf-8')
      dec_pattern = re.compile('================\[ Total CNF decisions \]================\s(\d+.?\d*)')
      dec_matches = dec_pattern.search(output)

      if dec_matches:
        if not Fields.SIZE in results:
          results[Fields.SIZE] = {}
        results[Fields.SIZE][mode] = int(float(dec_matches.group(1)))
      
      
      if not dec_matches :
        if not Fields.SIZE in results:
          results[Fields.SIZE] = {}
        results[Fields.SIZE][mode] = -1
        print('ERROR:')
        print(output)

    except subprocess.TimeoutExpired:
      print('TIMEOUT')
      p.terminate()

  print()
  
  return results

def main():
  parser = argparse.ArgumentParser(description="Test harness for Dice experiments.")
  parser.add_argument('-i', '--dir', type=str, nargs=1, help='directory of experiment Dice files')
  parser.add_argument('-d', '--dice', type=str, nargs=1, help='path to Dice')
  parser.add_argument('-o', '--out', type=str, nargs='?', const='results.json', default='results.json', help='path to output file. Defaults to results.json')
  parser.add_argument('--table', action='store_true', help='prints data from output file as Latex table')
  parser.add_argument('--plot', action='store_true', help='generate plots')
  parser.add_argument('--columns', nargs='+', type=Modes.from_string, choices=list(Modes), help='select modes to include in the table or plot')

  parser.add_argument('--timeout', type=int, nargs=1, help='sets timeout in seconds')
  parser.add_argument('-t', '--time', dest='fields', action='append_const', const=Fields.TIME, help='record time elapsed')
  parser.add_argument('-s', '--size', dest='fields', action='append_const', const=Fields.SIZE, help='record BDD size')
  parser.add_argument('-c', '--calls', dest='fields', action='append_const', const=Fields.CALLS, help='record number of recursive calls')
  parser.add_argument('-f', '--flips', dest='fields', action='append_const', const=Fields.FLIPS, help='record number of flips')
  parser.add_argument('-p', '--params', dest='fields', action='append_const', const=Fields.PARAMS, help='record number of parameters')
  parser.add_argument('-dp', '--distinct', dest='fields', action='append_const', const=Fields.DISTINCT, help='record number of distinct parameters')

  parser.add_argument('--problog', action='store_true', help='runs Problog programs')
  parser.add_argument('--cnf', action='store_true', help="runs Dice with sharpSAT")

  parser.add_argument('--modes', nargs='*', type=Modes.from_string, choices=list(Modes), help='select modes to run over')

  args = parser.parse_args()
  
  out = args.out

  old_data = {
    'timeouts': {m:None for m in Modes},
    'results': {}
  }

  if os.path.exists(out):
    with open(out, 'r') as f:
      old_data = json.load(f)

  if args.problog:
    files = args.dir[0]
    results = {}
    if not os.path.isdir(files):
      print('Invalid directory specified:', files)
      exit(2)
    else:
      print('Experiment dir:', files)
      print('Output file:', out)

      if args.timeout:
        print('Timeout:', args.timeout[0])
        timeout = args.timeout[0]
      else:
        timeout = None

      print()

      for filename in os.listdir(files):
        file = os.path.join(files, filename)
        if os.path.isfile(file) and os.path.splitext(file)[-1].lower() == '.pl':
          results[filename] = problog(file, timeout)

      print()
      
    with open('problog_results.json', 'w') as f:
      json.dump(results, f, indent=4)

  elif args.cnf:
    files = args.dir[0]
    out = 'cnf_results.json'
    if os.path.exists(out):
      with open(out) as f:
        results = json.load(f)
    else:
      results = {}
    if not os.path.isdir(files):
      print('Invalid directory specified:', files)
      exit(2)
    else:
      print('Experiment dir:', files)
      print('Output file:', out)

      if args.timeout:
        print('Timeout:', args.timeout[0])
        timeout = args.timeout[0]
      else:
        timeout = None

      if args.dice:
        dice_path = args.dice[0]
      else:
        dice_path = './'

      print()

      for filename in os.listdir(files):
        file = os.path.join(files, filename)
        if os.path.isfile(file) and os.path.splitext(file)[-1].lower() == '.dice':
          if filename in results:
            file_results = results[filename]
          else:
            file_results = {}
          if not Fields.SIZE in file_results:
            modes = [Modes.DET, Modes.FH]
            file_results[Fields.SIZE] = {m:None for m in modes}
          results[filename] = cnf(file, dice_path, timeout, file_results)

      print()
      
    with open(out, 'w') as f:
      json.dump(results, f, indent=4)

  elif args.dir:
    files = args.dir[0]
    if not os.path.isdir(files):
      print('Invalid directory specified:', files)
      exit(2)
    else:
      print('Experiment dir:', files)
      print('Output file:', out)

      if args.timeout:
        print('Timeout:', args.timeout[0])
        timeout = args.timeout[0]
      else:
        timeout = None

      fields = args.fields or []

      if args.dice:
        dice_path = args.dice[0]
      else:
        dice_path = './'

      if args.modes:
        modes = args.modes
      else:
        print('Please select at least one mode')
        exit(2)

      for m in modes:
        old_data['timeouts'][m] = timeout

      print()

      if 'results' in old_data:
        results = old_data['results']
      else:
        results = {}

      for filename in sorted(os.listdir(files)):
        file = os.path.join(files, filename)
        if os.path.isfile(file) and os.path.splitext(file)[-1].lower() == '.dice':
          if filename in results:
            file_results = results[filename]
          else:
            file_results = {}

          for f in fields:
            if not f in file_results:
              file_results[f] = {m:None for m in modes}
            else:
              for m in modes:
                if not m in file_results[f]:
                  file_results[f][m] = None

          try:
            results[filename] = run(file, dice_path, timeout, fields, modes, file_results)
          except KeyboardInterrupt:
            break

      print()

    old_data['results'] = results
      
    with open(out, 'w') as f:
      json.dump(old_data, f, indent=4)

  if args.table:
    print('========= Table =========')

    if not old_data['results']:
      print('ERRORS: No results to use')
      exit(2)
    
    old_results = old_data['results']

    table = Template("""\\begin{table}[h]
\\caption{$caption}
\\begin{tabular}{$alignments}
\\toprule
Benchmarks & $columns \\\\
\\midrule
$rows
\\bottomrule
\\end{tabular}
\\end{table}""")

    for f in Fields:
      modes = args.columns or Modes
      columns = " & ".join(map(Modes.to_column, modes))
      alignments = 'l' + 'r' * len(modes)
      rows = []
      max_col_vals = {}

      make_table = True
      for filename in old_results.keys():
        if not f in old_results[filename]:
          make_table = False
      
      if make_table:
        for filename in sorted(old_results.keys()):
          cols = []
        
          for m in modes:
            if m in old_results[filename][f] and old_results[filename][f][m]:
              cols.append(old_results[filename][f][m])

          max_col_vals[filename] = min(cols) if cols else None

        for filename in sorted(old_results.keys()):
          cols = ['\\textsc{' + filename.split('.')[0].replace('_', '\_') + '}']
        
          for m in modes:
            if f == Fields.TIME:
              if m in old_results[filename][f] and old_results[filename][f][m] and max_col_vals[filename]:
                if old_results[filename][f][m] == -1:
                  cols.append('*')
                else:
                  if round(old_results[filename][f][m], 2) == round(max_col_vals[filename], 2):
                    cols.append('\\textbf{%.2f}' % old_results[filename][f][m])
                  else:
                    cols.append('%.2f' % old_results[filename][f][m])
              else:
                cols.append('-')
            else:
              if m in old_results[filename][f] and old_results[filename][f][m] and max_col_vals[filename]:
                if old_results[filename][f][m] == -1:
                  cols.append('*')
                else:
                  if round(old_results[filename][f][m], 2) == round(max_col_vals[filename], 2):
                    cols.append('\\textbf{%s}' % "{:,}".format(old_results[filename][f][m]))
                  else:
                    cols.append("{:,}".format(old_results[filename][f][m]))
              else:
                cols.append('-')

          rows.append(' & '.join(cols) + ' \\\\')
      
        rows = '\n'.join(rows)

        caption = '%s Results' % str(f).capitalize()
        print(table.substitute(caption=caption, alignments=alignments, columns=columns, rows=rows))
    

  if args.plot:
    print('========= Plot =========')

    if not old_data['results']:
      print('ERRORS: No results to use')
      exit(2)
    
    old_results = old_data['results']

    colors = [
      'tab:blue', 
      'tab:orange', 
      'tab:green', 
      'tab:red', 
      'tab:purple', 
      'tab:brown', 
      'tab:pink', 
      'tab:gray', 
      'tab:olive'
    ]

    modes = args.columns or Modes

    # time cactus plot
    labels = ['Original', 'With Local Flip-Hoisting']
    for m, color, label in zip(modes, colors, labels):
      y_data = []
      y_timeouts = []
      for filename in old_results.keys():
        if m in old_results[filename][Fields.TIME] and old_results[filename][Fields.TIME][m]:
          # y_data.append(old_results[filename][Fields.TIME][m])
          y_data.append(math.log(old_results[filename][Fields.TIME][m]))
        else:
          # y_timeouts.append(old_data['timeouts'][m])
          y_timeouts.append(math.log(old_data['timeouts'][m]))

      y_data.sort()

      y_timeouts = y_data[-1:] + y_timeouts

      x_data = [x for x in range(len(y_data))]
      x_timeouts = [x + len(x_data) - 1 for x in range(len(y_timeouts))]

      plt.plot(x_data, y_data, 'o-', color=color, label=label)
      plt.plot(x_timeouts, y_timeouts, 'x-', color=color)

    plt.xlabel('Benchmarks')
    # plt.ylabel('Time (s)')
    plt.ylabel('Time (log s)')
    plt.legend()

    plt.grid(True, ls=':')

    plot_name = 'time_cactus.png'

    plt.savefig(plot_name, bbox_inches='tight')
    print('Saved to %s' % plot_name)

    # size plot
    plt.figure(figsize=(20,15))
    width = 0.4
    files = sorted(old_results.keys())
    x_data = [x for x in range(len(files))]

    for m, color, label in zip(modes, colors, labels):
      y_data = []
      y_timeouts = []
      for filename in files:
        if m in old_results[filename][Fields.SIZE] and old_results[filename][Fields.SIZE][m] \
          and old_results[filename][Fields.SIZE][m] != -1:
          # y_data.append(old_results[filename][Fields.SIZE][m])
          y_data.append(math.log(old_results[filename][Fields.SIZE][m], 10))
        else:
          y_data.append(0)

      plt.bar(x_data, y_data, color=color, width=width, label=label)
      x_data = [x+width for x in x_data]
      # plt.plot(x_timeouts, y_timeouts, 'x-', color=color)

    labels = [f.split('.')[0] for f in files]
    half_width = (x_data[0] - width) / 2
    x_data = [x-width-half_width for x in x_data]
    plt.xticks(x_data, labels, rotation=-45, ha="left", rotation_mode="anchor")
    plt.xlabel('Benchmarks')
    # plt.ylabel('BDD Size')
    plt.ylabel('BDD Size (log10)')
    plt.legend()

    plt.grid(True, ls=':')

    plot_name = 'size_cactus.png'

    plt.savefig(plot_name, bbox_inches='tight')
    print('Saved to %s' % plot_name)

    # time to flips 
    # plt.figure()
    # for m, color in zip(modes, colors):
    #   data = []
    #   for filename in old_results.keys():
    #     if m in old_results[filename][Fields.TIME] and old_results[filename][Fields.TIME][m]:
    #       y = old_results[filename][Fields.TIME][m]
    #       y_timeout = True
    #     else:
    #       y = old_data['timeouts'][m]
    #       y_timeout = False
        
    #     if m in old_results[filename][Fields.FLIPS] and old_results[filename][Fields.FLIPS][m]:
    #       x = old_results[filename][Fields.FLIPS][m]
    #       data.append((x, y, y_timeout))

    #   data.sort(key=lambda d: d[0])

    #   y_data = [d[1] for d in data]
    #   y_no_timeouts = [d[1] for d in data if d[2]]
    #   x_no_timeouts = [i for i in range(len(data)) if data[i][2]]
    #   y_timeouts = [d[1] for d in data if not d[2]]
    #   x_timeouts = [d[0] for d in data if not d[2]]
    #   x_data = [d[0] for d in data]

    #   plt.plot(x_data, y_data, 'o-', color=color, label=m, markevery=x_no_timeouts)
    #   # plt.plot(x_timeouts, y_timeouts, 'x-', color=color)

    # plt.xlabel('Flips')
    # plt.ylabel('Time (s)')
    # plt.legend()

    # plt.grid(True, ls=':')

    # plot_name = 'flips2time.png'

    # plt.savefig(plot_name, bbox_inches='tight')
    # print('Saved to %s' % plot_name)

if __name__ == '__main__':
  main()
