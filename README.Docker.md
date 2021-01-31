Step 1: create the Docker image:

    docker build --tag blockchain-voting:20210131 .


Step 2: create a container

    docker create --name prototype --tty --interactive blockchain-voting:20210131

Step 3: run the container

    docker start --attach --interactive prototype
