{
  description = "MODOS - MultiOmics Digital Object System";

  inputs = {
    # Nixpkgs
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    # The devenv module to create good development shells.
    devenv = {
      url = "github:cachix/devenv/latest";
      inputs.nixpkgs.follows = "nixpkgsDevenv";
    };
    # We should lock the pkgs in `mkShell` here:
    # https://github.com/cachix/devenv/issues/1797
    # to devenvs rolling nixpkgs. Note: that does not restrict the use of
    # 'nixpkgs' input in devenv modules.
    nixpkgsDevenv.url = "github:cachix/devenv-nixpkgs/rolling";
  };

  outputs =
    inputs:
    inputs.flake-utils.lib.eachDefaultSystem
      # Creates an attribute map `{ devShells.<system>.default = ...}`
      # by calling this function:
      (
        system:
        let
          # Import nixpkgs and load it into pkgs.
          pkgs = import inputs.nixpkgs {
            inherit system;
          };

          # Things needed at build-time.
          packages = with pkgs; [
            bash
            coreutils
            curl
            findutils
            git
            git-cliff
            just
            pyright
            uv
            zsh
          ];
        in
        {
          devShells = {
            default = inputs.devenv.lib.mkShell {
              inherit inputs;
              pkgs = inputs.nixpkgsDevenv.legacyPackages.${system};

              modules = [
                { inherit packages; }
              ];
            };
          };
        }
      );
}
