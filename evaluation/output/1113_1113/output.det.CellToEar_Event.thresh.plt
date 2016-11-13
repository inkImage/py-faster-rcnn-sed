## GNUPLOT command file
set terminal postscript color
set style data lines
set title 'Threshold Plot for CellToEar Event'
set xlabel 'Detection Score'
set grid
set size ratio 0.85
plot [0.101000:0.977000]  \
  'output.det.CellToEar_Event.dat.1' using 1:4 title 'PMiss' with lines lt 2, \
  'output.det.CellToEar_Event.dat.1' using 1:5 title 'RFA' with lines lt 3, \
  'output.det.CellToEar_Event.dat.1' using 1:6 title 'DCR' with lines lt 4, \
  'output.det.CellToEar_Event.dat.2' using 1:2 title 'Min DCR 0.885, scr 0.320' with points lt 6
