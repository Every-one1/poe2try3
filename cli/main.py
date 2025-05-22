# Placeholder for cli/main.py
# This file will be the new main entry point for Click.
import click

@click.group()
def cli():
    """Path of Exile 2 Information Tool CLI"""
    pass

# Example command (can be expanded later)
@cli.command("greet")
@click.argument('name')
def greet(name):
    """Greets a person."""
    click.echo(f"Hello {name}!")

if __name__ == '__main__':
    cli()
