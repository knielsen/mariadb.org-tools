# The default build steps used here are defined in the builders/connectors-buildsteps.py
connodbc_linux_step0_checkout= step0_checkout("https://github.com/MariaDB-Corporation/mariadb-connector-odbc.git") + step0_set_test_env + """
export TEST_DRIVER=maodbc_test
export TEST_DSN=maodbc_test
"""
connodbc_linux_step1_build= step1_build
connodbc_linux_step2_serverinstall= linux_serverinstall
#Step 3 - package quality test step - to add
connodbc_linux_step3_packagetest= ""
connodbc_linux_step4_1_testenvertup= """cd ./build/test
cat odbcinst.ini
cat odbc.ini
export ODBCINI="$PWD/odbc.ini"
export ODBCSYSINI=$PWD
export TEST_SKIP_UNSTABLE_TEST=1
cd ../..
"""
connodbc_linux_step4_testsrun= connodbc_linux_step4_1_testenvertup + step4_testsrun
connodbc_linux_step4_valgrindtest= """
cd ./build/test
ls -l
for odbctest in ./odbc_*; do
  if [ -x "$odbctest" ]; then
    memcheck="$odbctest.memcheck"
    valgrind --leak-check=full $odbctest 2> $memcheck | grep -B 5 "not ok" || true
#cat $memcheck
    leaked1=$(grep "definitely lost: " $memcheck | sed -e 's/^==[0-9]*==//' -e 's/[^0-9]//g' -e 's/00/0/')
    leaked2=$(grep "indirectly lost: " $memcheck | sed -e 's/^==[0-9]*==//' -e 's/[^0-9]//g' -e 's/00/0/')
    echo "Definetely: $leaked1 indirectly: $leaked2"

    if [ "$leaked1" -gt 0 ] || [ "$leaked2" -gt 0 ]; then
      echo "$odbctest Leaked"
      HASLEAKS=1
    else
      echo "$odbctest is clean"
    fi
  fi
done
if [ ! -z $HASLEAKS ]; then
  false
fi
"""

def connector_odbc_valgrind_memcheck(name, kvm_image, cflags, cmake_params, slaves=connector_slaves):
    linux_connector_odbc= BuildFactory()
    args= ["--port="+getport(), "--user=buildbot", "--smp=4", "--cpu=host"]
    linux_connector_odbc.addStep(ShellCommand(
        description=["cleaning", "build", "dir"],
        descriptionDone=["clean", "build", "dir"],
        command=["sh", "-c", "rm -Rf ../build/*"]))
    linux_connector_odbc.addStep(ShellCommand(
        description=["rsyncing", "VMs"],
        descriptionDone=["rsync", "VMs"],
        doStepIf=(lambda(step): step.getProperty("slavename") != "bb01"),
        haltOnFailure=True,
        command=["rsync", "-a", "-v", "-L",
                 "bb01.mariadb.net::kvm/vms/"+kvm_image+"-build.qcow2",
                 "/kvm/vms/"]))
    linux_connector_odbc.addStep(Compile(
        description=["building", "linux-connctor_odbc"],
        descriptionDone=["build", "linux-connector_odbc"],
        timeout=3600,
        env={"TERM": "vt102"},
        command=["runvm", "--base-image=/kvm/vms/"+kvm_image+"-build.qcow2"] + args +["vm-tmp-"+getport()+".qcow2",
        "rm -Rf buildbot && mkdir buildbot",
        WithProperties("""
export CFLAGS="${CFLAGS}"""+ cflags + """"
sudo apt-get update
sudo apt-get install -y valgrind
""" +
connodbc_linux_step0_checkout + """
cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCONC_WITH_UNIT_TESTS=Off -DPACKAGE_PLATFORM_SUFFIX=$HOSTNAME""" + cmake_params + """ ../src""" +
connodbc_linux_step1_build +
connodbc_linux_step2_serverinstall +
connodbc_linux_step4_1_testenvertup +
connodbc_linux_step4_valgrindtest),
        ]))
    return {'name': name, 'builddir': name,
            'factory': linux_connector_odbc,
            "slavenames": slaves,
            "category": "connectors"}

def build_linux_connector_odbc(name, kvm_image, cflags, cmake_params, slaves=connector_slaves):
    linux_connector_odbc= BuildFactory()
    args= ["--port="+getport(), "--user=buildbot", "--smp=4", "--cpu=host"]
    linux_connector_odbc.addStep(ShellCommand(
        description=["cleaning", "build", "dir"],
        descriptionDone=["clean", "build", "dir"],
        command=["sh", "-c", "rm -Rf ../build/*"]))
    linux_connector_odbc.addStep(ShellCommand(
        description=["rsyncing", "VMs"],
        descriptionDone=["rsync", "VMs"],
        doStepIf=(lambda(step): step.getProperty("slavename") != "bb01"),
        haltOnFailure=True,
        command=["rsync", "-a", "-v", "-L",
                 "bb01.mariadb.net::kvm/vms/"+kvm_image+"-build.qcow2",
                 "/kvm/vms/"]))
    linux_connector_odbc.addStep(Compile(
        description=["building", "linux-connctor_odbc"],
        descriptionDone=["build", "linux-connector_odbc"],
        timeout=3600,
        env={"TERM": "vt102"},
        command=["runvm", "--base-image=/kvm/vms/"+kvm_image+"-build.qcow2"] + args +["vm-tmp-"+getport()+".qcow2",
        "rm -Rf buildbot && mkdir buildbot",
        WithProperties("""
export CFLAGS="${CFLAGS}"""+ cflags + """" """ +
connodbc_linux_step0_checkout + """
cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCONC_WITH_UNIT_TESTS=Off -DPACKAGE_PLATFORM_SUFFIX=$HOSTNAME""" + cmake_params + """ ../src""" +
connodbc_linux_step1_build +
connodbc_linux_step2_serverinstall +
connodbc_linux_step3_packagetest +
connodbc_linux_step4_testsrun
),
        "= scp -r -P "+getport()+" "+kvm_scpopt+" buildbot@localhost:/home/buildbot/build/mariadb*tar.gz .",
        ]))
    linux_connector_odbc.addStep(SetPropertyFromCommand(
        property="bindistname",
        command=["sh", "-c", WithProperties("basename `ls mariadb*odbc*tar.gz`")],
        ))
    addPackageUploadStep(linux_connector_odbc, '"%(bindistname)s"')
    return {'name': name, 'builddir': name,
            'factory': linux_connector_odbc,
            "slavenames": slaves,
            "category": "connectors"}

def build_linux_connector_odbc_no_test(name, kvm_image, cflags, cmake_params, slaves=connector_slaves):
    linux_connector_odbc= BuildFactory()
    args= ["--port="+getport(), "--user=buildbot", "--smp=4", "--cpu=host"]
    linux_connector_odbc.addStep(ShellCommand(
        description=["cleaning", "build", "dir"],
        descriptionDone=["clean", "build", "dir"],
        command=["sh", "-c", "rm -Rf ../build/*"]))
    linux_connector_odbc.addStep(ShellCommand(
        description=["rsyncing", "VMs"],
        descriptionDone=["rsync", "VMs"],
        doStepIf=(lambda(step): step.getProperty("slavename") != "bb01"),
        haltOnFailure=True,
        command=["rsync", "-a", "-v", "-L",
                 "bb01.mariadb.net::kvm/vms/"+kvm_image+"-build.qcow2",
                 "/kvm/vms/"]))
    linux_connector_odbc.addStep(Compile(
        description=["building", "linux-connctor_odbc"],
        descriptionDone=["build", "linux-connector_odbc"],
        timeout=3600,
        env={"TERM": "vt102"},
        command=["runvm", "--base-image=/kvm/vms/"+kvm_image+"-build.qcow2"] + args +["vm-tmp-"+getport()+".qcow2",
        "rm -Rf buildbot && mkdir buildbot",
        WithProperties("""
export CFLAGS="${CFLAGS}"""+ cflags + """" """ +
connodbc_linux_step0_checkout + """
cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCONC_WITH_UNIT_TESTS=Off -DPACKAGE_PLATFORM_SUFFIX=$HOSTNAME""" + cmake_params + """ ../src""" +
connodbc_linux_step1_build
),
        "= scp -r -P "+getport()+" "+kvm_scpopt+" buildbot@localhost:/home/buildbot/build/mariadb*tar.gz .",
        ]))
    linux_connector_odbc.addStep(SetPropertyFromCommand(
        property="bindistname",
        command=["sh", "-c", WithProperties("basename `ls mariadb*odbc*tar.gz`")],
        ))
    addPackageUploadStep(linux_connector_odbc, '"%(bindistname)s"')
    return {'name': name, 'builddir': name,
            'factory': linux_connector_odbc,
            "slavenames": slaves,
            "category": "connectors"}

bld_codbc_amd64_valgrind= connector_odbc_valgrind_memcheck("codbc-focal-amd64-memcheck", "vm-focal-amd64", "", " -DWITH_SSL=OPENSSL");
bld_codbc_amd64_asan= build_linux_connector_odbc("codbc-linux-amd64-asan", "vm-jammy-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_ASAN=ON");
bld_codbc_amd64_ubsan= build_linux_connector_odbc("codbc-linux-amd64-ubsan", "vm-jammy-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_UBSAN=ON");
bld_codbc_amd64_msan= build_linux_connector_odbc("codbc-linux-amd64-msan", "vm-jammy-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_MSAN=ON");

bld_codbc_sles15_amd64= build_linux_connector_odbc("codbc-sles15-amd64", "vm-sles153-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");

bld_codbc_focal_amd64= build_linux_connector_odbc("codbc-focal-amd64", "vm-focal-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_focal_aarch64= build_linux_connector_odbc("codbc-focal-aarch64", "vm-focal-aarch64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON", slaves=connector_slaves_aarch64);

bld_codbc_buster_amd64= build_linux_connector_odbc("codbc-buster-amd64", "vm-buster-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_buster_aarch64= build_linux_connector_odbc("codbc-buster-aarch64", "vm-buster-aarch64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON", slaves=connector_slaves_aarch64);

bld_codbc_bullseye_amd64= build_linux_connector_odbc("codbc-bullseye-amd64", "vm-bullseye-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_bullseye_aarch64= build_linux_connector_odbc("codbc-bullseye-aarch64", "vm-bullseye-aarch64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON", slaves=connector_slaves_aarch64);

bld_codbc_bookworm_amd64= build_linux_connector_odbc("codbc-bookworm-amd64", "vm-bookworm-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_bookworm_aarch64= build_linux_connector_odbc("codbc-bookworm-aarch64", "vm-bookworm-aarch64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON", slaves=connector_slaves_aarch64);

bld_centos7_x64_connector_odbc_new= build_linux_connector_odbc("codbc-centos7-amd64", "vm-centos74-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_rhel8_amd64= build_linux_connector_odbc("codbc-rhel8-amd64", "vm-rhel8-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
# We can't install server here or this time-outs with high probability

bld_codbc_jammy_amd64= build_linux_connector_odbc("codbc-jammy-amd64", "vm-jammy-amd64", "", " -DWITH_SSL=OPENSSL");
bld_codbc_jammy_aarch64= build_linux_connector_odbc_no_test("codbc-jammy-aarch64", "vm-jammy-aarch64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON", slaves=connector_slaves_aarch64);

bld_codbc_kinetic_amd64= build_linux_connector_odbc_no_test("codbc-kinetic-amd64", "vm-kinetic-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");

bld_codbc_lunar_amd64= build_linux_connector_odbc_no_test("codbc-lunar-amd64", "vm-lunar-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");

bld_codbc_fedora36_amd64= build_linux_connector_odbc_no_test("codbc-fedora36-amd64", "vm-fedora36-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_fedora37_amd64= build_linux_connector_odbc_no_test("codbc-fedora37-amd64", "vm-fedora37-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_fedora38_amd64= build_linux_connector_odbc_no_test("codbc-fedora38-amd64", "vm-fedora38-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");

#bld_codbc_rhel9_amd64= build_linux_connector_odbc("codbc-rhel9-amd64", "vm-rhel9-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_rhel9_amd64= build_linux_connector_odbc_no_test("codbc-rhel9-amd64", "vm-rhel9-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_rhel9_aarch64= build_linux_connector_odbc_no_test("codbc-rhel9-aarch64", "vm-rhel9-aarch64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON", slaves=connector_slaves_aarch64);

bld_codbc_rhel8_aarch64= build_linux_connector_odbc_no_test("codbc-rhel8-aarch64", "vm-rhel8-aarch64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON", slaves=connector_slaves_aarch64);
bld_codbc_rocky8_aarch64= build_linux_connector_odbc_no_test("codbc-rocky8-aarch64", "vm-rocky8-aarch64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON", slaves=connector_slaves_aarch64);

bld_codbc_sles12_amd64= build_linux_connector_odbc_no_test("codbc-sles12-amd64", "vm-sles123-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");

# Tests on bionic usually/too often time-out
bld_codbc_bionic_amd64= build_linux_connector_odbc_no_test("codbc-bionic-amd64", "vm-bionic-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");
bld_codbc_bionic_aarch64= build_linux_connector_odbc_no_test("codbc-bionic-aarch64", "vm-bionic-aarch64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON", slaves=connector_slaves_aarch64);

bld_codbc_sles15_amd64_notest= build_linux_connector_odbc_no_test("codbc-sles15-amd64-notest", "vm-sles153-amd64", "", " -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON");

##################### RPM/DEB builders ###################

def build_connector_odbc_rpm(name, kvm_image, cflags, cmake_params):
    linux_connector_odbc= BuildFactory()
    args= ["--port="+getport(), "--user=buildbot", "--smp=4", "--cpu=host"]
    linux_connector_odbc.addStep(ShellCommand(
        description=["cleaning", "build", "dir"],
        descriptionDone=["clean", "build", "dir"],
        command=["sh", "-c", "rm -Rf ../build/*"]))
    linux_connector_odbc.addStep(ShellCommand(
        description=["rsyncing", "VMs"],
        descriptionDone=["rsync", "VMs"],
        doStepIf=(lambda(step): step.getProperty("slavename") != "bb01"),
        haltOnFailure=True,
        command=["rsync", "-a", "-v", "-L",
                 "bb01.mariadb.net::kvm/vms/"+kvm_image+"-build.qcow2",
                 "bb01.mariadb.net::kvm/vms/"+kvm_image+"-install.qcow2",
                 "/kvm/vms/"]))
    linux_connector_odbc.addStep(Compile(
        description=["building", "linux-connctor_odbc"],
        descriptionDone=["build", "linux-connector_odbc"],
        timeout=3600,
        env={"TERM": "vt102"},
        command=["runvm", "--base-image=/kvm/vms/"+kvm_image+"-build.qcow2"] + args +["vm-tmp-"+getport()+".qcow2",
        "rm -Rf buildbot && mkdir buildbot",
        WithProperties("""
export CFLAGS="${CFLAGS}"""+ cflags + """" """ +
connodbc_linux_step0_checkout + """
mv ../src/libmariadb ../
mkdir ../concbuild
cd ../concbuild
cmake ../libmariadb -DCMAKE_BUILD_TYPE=RelWithDebInfo -DWITH_UNIT_TESTS=Off
cmake --build . --config RelWithDebInfo
sudo make install
cd ../build
cmake RPM=On -DCPACK_GENERATOR=RPM -DWITH_UNIT_TESTS=Off -DCMAKE_BUILD_TYPE=RelWithDebInfo -DMARIADB_LINK_DYNAMIC=On -DCMAKE_C_FLAGS_RELWITHDEBINFO="-L/usr/local/lib/mariadb" -DPACKAGE_PLATFORM_SUFFIX=$HOSTNAME""" + cmake_params + """ ../src""" +
connodbc_linux_step1_build
),
        "= scp -r -P "+getport()+" "+kvm_scpopt+" buildbot@localhost:/home/buildbot/build/mariadb*rpm .",
        ]))
    linux_connector_odbc.addStep(SetPropertyFromCommand(
        property="bindistname",
        command=["sh", "-c", WithProperties("basename `ls mariadb*odbc*rpm`")],
        ))
    addPackageUploadStep(linux_connector_odbc, '"%(bindistname)s"')
    linux_connector_odbc.addStep(Test(
        description=["testing", "install"],
        descriptionDone=["test", "install"],
        logfiles={"kernel": "kernel_"+getport()+".log"},
        env={"TERM": "vt102"},
        command=["runvm", "--base-image=/kvm/vms/"+kvm_image+"-install.qcow2"] + args + ["vm-tmp-"+getport()+".qcow2",
        "rm -Rf buildbot && mkdir buildbot",
        "= scp -r -P "+getport()+" "+kvm_scpopt+" $(find . -name mariadb*odbc*rpm ) buildbot@localhost:buildbot/",
        WithProperties("""
set -ex
ls
cd buildbot
ls
if [ -f /usr/bin/subscription-manager ] ; then sudo subscription-manager refresh ;fi
sudo yum -y --nogpgcheck install %(bindistname)s
garbd --version
""")]))
    return {'name': name, 'builddir': name,
            'factory': linux_connector_odbc,
            "slavenames": connector_slaves,
            "category": "connectors"}

def build_connector_odbc_deb(name, kvm_image, cflags, cmake_params):
    linux_connector_odbc= BuildFactory()
    args= ["--port="+getport(), "--user=buildbot", "--smp=4", "--cpu=host"]
    linux_connector_odbc.addStep(ShellCommand(
        description=["cleaning", "build", "dir"],
        descriptionDone=["clean", "build", "dir"],
        command=["sh", "-c", "rm -Rf ../build/*"]))
    linux_connector_odbc.addStep(ShellCommand(
        description=["rsyncing", "VMs"],
        descriptionDone=["rsync", "VMs"],
        doStepIf=(lambda(step): step.getProperty("slavename") != "bb01"),
        haltOnFailure=True,
        command=["rsync", "-a", "-v", "-L",
                 "bb01.mariadb.net::kvm/vms/"+kvm_image+"-build.qcow2",
                 "/kvm/vms/"]))
    linux_connector_odbc.addStep(Compile(
        description=["building", "linux-connctor_odbc"],
        descriptionDone=["build", "linux-connector_odbc"],
        timeout=3600,
        env={"TERM": "vt102"},
        command=["runvm", "--base-image=/kvm/vms/"+kvm_image+"-build.qcow2"] + args +["vm-tmp-"+getport()+".qcow2",
        "rm -Rf buildbot && mkdir buildbot",
        WithProperties("""
export CFLAGS="${CFLAGS}"""+ cflags + """" """ +
connodbc_linux_step0_checkout + """
mv ../src/libmariadb ../
mkdir ../concbuild
cd ../concbuild
cmake ../libmariadb -DCMAKE_BUILD_TYPE=RelWithDebInfo -DWITH_UNIT_TESTS=Off
cmake --build . --config RelWithDebInfo
sudo make install
cd ../build
cmake -DDEB=On -DCPACK_GENERATOR=DEB -DWITH_UNIT_TESTS=Off -DCMAKE_BUILD_TYPE=RelWithDebInfo -DMARIADB_LINK_DYNAMIC=On -DCMAKE_C_FLAGS_RELWITHDEBINFO="-L/usr/local/lib/mariadb" -DPACKAGE_PLATFORM_SUFFIX=$HOSTNAME""" + cmake_params + """ ../src""" +
connodbc_linux_step1_build
),
        "= scp -r -P "+getport()+" "+kvm_scpopt+" buildbot@localhost:/home/buildbot/build/mariadb*deb .",
        ]))
    linux_connector_odbc.addStep(SetPropertyFromCommand(
        property="bindistname",
        command=["sh", "-c", WithProperties("basename `ls mariadb*odbc*deb`")],
        ))
    addPackageUploadStep(linux_connector_odbc, '"%(bindistname)s"')
    linux_connector_odbc.addStep(Test(
        description=["testing", "install"],
        descriptionDone=["test", "install"],
        logfiles={"kernel": "kernel_"+getport()+".log"},
        env={"TERM": "vt102"},
        command=["runvm", "--base-image=/kvm/vms/"+kvm_image+"-install.qcow2"] + args + ["vm-tmp-"+getport()+".qcow2",
        "rm -Rf buildbot && mkdir buildbot",
        "= scp -r -P "+getport()+" "+kvm_scpopt+" */mariadb*odbc*deb buildbot@localhost:buildbot/",
        WithProperties("""
set -ex
ls
cd buildbot
ls
for i in 1 2 3 4 5 6 7 8 9 10 ; do
  if sudo apt-get update ; then
      break
  fi
  echo "Installation warning: apt-get update failed, retrying ($i)"
  sleep 10
done

sudo sh -c "DEBIAN_FRONTEND=noninteractive apt-get install --allow-unauthenticated -y ./%(bindistname)s"
sudo sh -c "DEBIAN_FRONTEND=noninteractive apt-get install --allow-unauthenticated -y unixodbc"
export CFLAGS="${CFLAGS}"""+ cflags + """" """ +
connodbc_linux_step0_checkout + """
rm -rf ../src/libmariadb
sudo sh -c "DEBIAN_FRONTEND=noninteractive apt-get install --allow-unauthenticated -y cmake"
cmake -DBUILD_TESTS_ONLY=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo -DMARIADB_LINK_DYNAMIC=On -DCMAKE_C_FLAGS_RELWITHDEBINFO="-L/usr/local/lib/mariadb" """ + cmake_params + """ ../src
cmake --build . --config RelWithDebInfo
""" + connodbc_linux_step2_serverinstall + connodbc_linux_step4_testsrun)]))
    return {'name': name, 'builddir': name,
            'factory': linux_connector_odbc,
            "slavenames": connector_slaves,
            "category": "connectors"}

bld_rhel8_x64_connector_odbc_rpm= build_connector_odbc_rpm("codbc-rhel8-amd64-rpm", "vm-rhel8-amd64", "", " -DWITH_SSL=OPENSSL");

bld_rhel9_x64_connector_odbc_rpm= build_connector_odbc_rpm("codbc-rhel9-amd64-rpm", "vm-rhel9-amd64", "", " -DWITH_SSL=OPENSSL");

bld_codbc_focal_amd64_deb= build_connector_odbc_deb("codbc-focal-amd64-deb", "vm-focal-amd64", "", " -DWITH_SSL=OPENSSL");

