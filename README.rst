====
mkpi
====

Easy custom raspbian/debian images on for your raspberry pi.

The script is a bit like the old ``ubuntu-vm-builder`` package, but produces
images for raspberry pi that can be burnt to SD card with ``dd``.

Usage
=====

You need some dependencies first::

    sudo apt-get install binfmt-support qemu-user-static debootstrap kpartx dosfstools

You can install ``mkpi`` and its dependencies with ``pip``::

    sudo pip install mkpi

or ``easy_install``::

    sudo easy_install mkpi

It's better to install it in a ``virtualenv`` so it's easier to remove.

Then you can make your first image with::

    sudo mkpi


Hacking
=======

Checkout the repo, create a virtualenv and do an editable install::

    git clone git://github.com/Jc2k/mkpi
    cd mkpi
    virtualenv .
    source bin/activate
    pip install -e .

