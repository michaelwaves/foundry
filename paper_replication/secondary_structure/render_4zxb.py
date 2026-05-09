from pymol import cmd

TYPE = "beta"

cmd.fetch("4zxb")
cmd.hide("everything")

if TYPE == "alpha":
    # cmd.fab("EAAAKEAAAKEAAAKEAAAKEAAAKEAAAKEAAAKEAAAK", "helix", ss=1)
    cmd.select("helix", "resi 695-709")
    print(cmd.get_fastastr("resi 695-709"))
    cmd.show("line", "helix and chain E")
    cmd.orient("helix")
    cmd.zoom("helix")
else:
    # cmd.select("sheet_s1", "resi 12-20+1-9+50-56+42-46")
    cmd.select("sheet_s1", 'resi 857-862+842-851+880-890+901-905')
    cmd.show("cartoon", "sheet_s1 and chain E")
    print(cmd.get_fastastr('resi 857-862+842-851+880-890+901-905'))
    # cmd.color("salmon",    "resi 12-20")
    # cmd.color("skyblue",   "resi 1-9")
    # cmd.color("palegreen", "resi 50-56")
    # cmd.color("lightpink", "resi 42-46")
    cmd.orient("sheet_s1")
    cmd.zoom("sheet_s1")
    # cmd.fab("VTVTVTVTVTVTVTVTNPGTVTVTVTVTVTVTVTVTVTVT", "beta_peptide", ss=2)

cmd.bg_color("white")
cmd.ray(1600, 1200)   # high-quality render

if TYPE == "alpha":
    cmd.png("alpha_line_4zxb.png", dpi=300)
else:
    cmd.png("beta_4zxb.png", dpi=300)
