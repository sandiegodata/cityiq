
NFS Mounts in Docker, for versions later than 17.06

export NFS_VOL_NAME=mynfs
export NFS_LOCAL_MNT=/mnt/mynfs
export NFS_SERVER=my.nfs.server.com
export NFS_SHARE=/my/server/path
export NFS_OPTS=vers=4,soft

docker run --mount \ "src=$NFS_VOL_NAME,dst=$NFS_LOCAL_MNT,volume-opt=device=:$NFS_SHARE,\"volume-opt=o=addr=$NFS_SERVER,$NFS_OPTS\",type=volume,volume-driver=local,volume-opt=type=nfs" \
busybox ls $NFS_LOCAL_MNT

Or, create the volumne first:

docker volume create --driver local \
  --opt type=nfs --opt o=addr=$NFS_SERVER,$NFS_OPTS \
  --opt device=:$NFS_SHARE $NFS_VOL_NAME

docker run --rm -v $NFS_VOL_NAME:$NFS_LOCAL_MNT busybox ls $NFS_LOCAL_MNT

-----

docker volume create --driver local \
  --opt type=nfs --opt o=addr=nas2,vers=4,soft \
  --opt device=:cache nas2-cache

docker run --rm -v nas2-cache:/data busybox ls /data
