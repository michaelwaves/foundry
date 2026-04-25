from pymol import cmd
cmd.load("/mnt/nw/home/m.yu/repos/foundry/tutorials/rfd3_ppi_tutorial/outputs/2/ppi_tutorial_insulinr_0_model_0.cif")
# cmd.load("/mnt/nw/home/m.yu/repos/foundry/tutorials/rfd3_ppi_tutorial/4zxb_cropped.pdb")
print(cmd.get_fastastr("not chain B"))
cmd.color('orange', 'not chain B')
cmd.select('generated', 'not chain B')
cmd.hide(selection='chain B')
cmd.png('generated.png', width=1920, height=1080, dpi=300, ray=1)
