#! /usr/bin/env python

import os
import sys
import subprocess
import time
import contextlib2
import pkgutil
import ConfigParser


CONFIG_FILES = [
    "boot/cmdline.txt",
    "etc/fstab",
    "etc/network/interfaces",
    "etc/apt/sources.list",
    "etc/modules",
]


class MappedPartitions(object):

    def __init__(self, image_path):
        self.image_path = image_path

    def __enter__(self):
        print "> Setting up partitions in devmapper"
        mapper_table = subprocess.check_output(["kpartx", "-sva", self.image_path]).strip().splitlines()
        p0 = "/dev/mapper/" + mapper_table[0].split(" ")[2]
        print "   /boot=%s" % p0
        p1 = "/dev/mapper/" + mapper_table[1].split(" ")[2]
        print "   /=%s" % p1
        return p0, p1

    def __exit__(self, *exc):
        print "> Closing partitions"
        subprocess.check_call(["kpartx", "-dv", self.image_path])


class Mount(object):

    def __init__(self, *args):
        self.args = args

    def __enter__(self):
        path = self.args[-1]
        print "> Mounting %r" % path
        if not os.path.exists(path):
            os.makedirs(path)
        subprocess.check_call(["mount"] + list(self.args))

    def __exit__(self, *exc):
        path = self.args[-1]
        print "> Unmounting %r" % path
        for i in range(5):
            try:
                subprocess.check_call(["umount", "-vf", path])
            except:
                time.sleep(i)
                continue
            break
        else:
            print "UNMOUNT FAILED"


class Loopback(object):

    def __init__(self, image_path):
        self.image_path = image_path

    def __enter__(self):
        print "> Setting up loopback device"
        self.lo = subprocess.check_output(["losetup", "-f", "--show", self.image_path]).strip()
        print ".... device=%s" % self.lo
        return self.lo

    def __exit__(self, *exc):
        print "> Closing loopback device"
        subprocess.check_call(["losetup", "-d", self.lo])


def main():
    if os.getuid() != 0:
        print "You need to run this script as root"
        sys.exit(1)

    def is_on_path(binary):
        for d in os.environ.get("PATH", "").split(":"):
            if os.path.exists(os.path.join(d, binary)):
                return True
        return False

    for binary in ("kpartx", "mkfs.vfat", "mkfs.ext4", "losetup"):
        if not is_on_path(binary):
            print "Could not find %r on $PATH. Aborting." % binary
            sys.exit(1)

    cfg = ConfigParser.ConfigParser()
    cfg.read([os.path.join(os.path.dirname(__file__), "defaults.cfg")])

    chroot_path = os.path.join(os.getcwd(), "build-env")
    image_path = os.path.join(os.getcwd(), "raspbian_XXXX.img")

    if not os.path.exists(image_path):
        print "> Creating empty image file"
        subprocess.check_call(["dd", "if=/dev/zero", "of=%s" % image_path, "bs=1MB", "seek=3800", "count=1"])

    with Loopback(image_path) as loopback_device:
        print "> Partitioning image"
        p = subprocess.Popen(["fdisk", loopback_device], stdin=subprocess.PIPE)
        p.communicate("n\np\n1\n\n+64MB\nt\nc\nn\np\n2\n\n\nw\n")

    with contextlib2.ExitStack() as stack:
        p0, p1 = stack.enter_context(MappedPartitions(image_path))

        print "> Creating /boot as fat"
        subprocess.check_call(["mkfs.vfat", p0])

        print "> Creating / as ext4"
        subprocess.check_call(["mkfs.ext4", p1])

        stack.enter_context(Mount(p1, chroot_path))
        stack.enter_context(Mount(p0, os.path.join(chroot_path, "boot")))
        stack.enter_context(Mount("-t", "proc", "none", os.path.join(chroot_path, "proc")))
        stack.enter_context(Mount("-t", "sysfs", "none", os.path.join(chroot_path, "sysfs")))
        stack.enter_context(Mount("-o", "bind", "/dev", os.path.join(chroot_path, "dev")))
        #stack.enter_context(Mount("-o", "bind", "/dev/pts", os.path.join(chroot_path, "dev/pts")))

        # Could bind mount in an assets directory...
        # stack.enter_context(Mount("-o", "bind", "from", "to"))

        print "> Bootstrapping Raspbian"
        subprocess.check_call([
            "qemu-debootstrap", "--verbose",
            "--keyring=%s" % os.path.join(os.path.dirname(__file__), "raspbian-archive-keyring.gpg"),
            "--arch", "armhf",
            "--include=raspbian-archive-keyring,raspberrypi-bootloader-nokernel,libraspberrypi-bin",
            "--components=main,contrib,non-free,firmware,rpi",
            "wheezy",
            chroot_path,
            cfg.get("debootstrap", "repository"),
            ])

        for conf in CONFIG_FILES:
            print "> Writing %r" % conf
            with open(os.path.join(chroot_path, conf), "w") as fp:
                fp.write(pkgutil.get_data("mkpi", "files/" + conf.replace("/", "_")))

        print "> Setting hostname"
        with open(os.path.join(chroot_path, "etc", "hostname"), "w") as fp:
            fp.write("raspberrypi")

    print "> Done"
