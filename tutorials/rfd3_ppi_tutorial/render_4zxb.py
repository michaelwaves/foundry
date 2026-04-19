from pymol import cmd

PDB_PATH = "4zxb.pdb"


def main():
    cmd.load(PDB_PATH)
    cmd.color('green', 'chain E')
    cmd.color('magenta', 'not chain E')
    cmd.png("4zxb_full.png", width=1920, height=1080, dpi=300, ray=1)


if __name__ == "__main__":
    main()
