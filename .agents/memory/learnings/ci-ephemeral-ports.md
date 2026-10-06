# CI smoke tests bind ephemeral ports

Use `-p 127.0.0.1:0:PORT` + `docker port` to get the assigned port.
Fixed ports collide on shared/local daemons (3000 was already taken
when act ran the smoke step).
