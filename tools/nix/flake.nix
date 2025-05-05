{
  description = "MODOS - MultiOmics Digital Object System";

  inputs = {
    # Nixpkgs
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    # You can access packages and modules from different nixpkgs revs
    # at the same time. Here's an working example:
    nixpkgsStable.url = "github:nixos/nixpkgs/nixos-24.11";
    # Also see the 'stable-packages' overlay at 'overlays/default.nix'.

    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    nixpkgs,
    flake-utils,
    ...
  }:
    flake-utils.lib.eachDefaultSystem
    # Creates an attribute map `{ devShells.<system>.default = ...}`
    # by calling this function:
    (
      system: let
        # Import nixpkgs and load it into pkgs.
        pkgs = import nixpkgs {
          inherit system;
        };

        # Things needed at build-time.
        packagesBasic = with pkgs; [
          bash
          coreutils
          curl
          findutils
          git
          just
          pyright
          uv
          zsh
        ];

        # Things needed at runtime.
        buildInputs = [];
      in {
        devShells = {
          default = pkgs.mkShell {
            inherit buildInputs;
            nativeBuildInputs = packagesBasic;
          };
        };
      }
    );
}
