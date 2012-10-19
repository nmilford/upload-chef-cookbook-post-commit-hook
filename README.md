upload-chef-cookbook-post-commit-hook
=====================================

Subversion post commit hook that allows you to trigger a Chef cookbook upload.

Dedicated to those of us still living in the world of subversion :)

At Outbrain we use [Glu](https://github.com/linkedin/glu) for continious deployment where folks need only commit by adding #deploy:module to thier commit message.

Here we have more and more developers writing cookbooks (YAY!) and I wanted to make it dead simple for them to work with Chef using the same workflow they use in thier other projects. 

## Usage:

To trigger an upload simply add `#chefdeploy:cookbookName` to your commit
message like thus:

`svn ci chef-repo/cookbooks/myCookbook -m"Updated my cookbook #chefdeploy:myCookbook"`

The script will then download the cookbook on the subversion server, lint it, then upload it to Chef.

It will also email you on success or failure.

Success:
```
From: chefuser@example.com
To: nathan@example.com
Subject: Chef Deploy of myCookbook 0.0.27 on SVN commit 73349 was a success.
Date: Fri, 19 Oct 2012 11:07:51 -0400 (EDT)

Well done!

Command output is:

Uploading myCookbook      [0.0.27]
Uploaded 1 cookbook.
```

Failure:
```
From: chefuser@example.com
To: nathan@example.com
Subject: Chef Deploy of myCookbook on SVN commit 73348 failed.
Date: Fri, 19 Oct 2012 11:04:15 -0400 (EDT)

Execution of knife cookbook upload exited with status 256, command output is:

Uploading myCookbook      [0.0.27]
FATAL: Cookbook file recipes/foobar.rb has a ruby syntax error:
FATAL: /var/tmp/myCookbook/recipes/foobar.rb:38: syntax error, unexpected $end, expecting keyword_end
```

Note, this assumes your subversion username is the same as your email username and only works from your main subversion server, if you are running this from a downstream svnsync replica it will think the commits is svnsync :/

The script is also setup to hit graphite so you can [overlay events on metrics](http://codeascraft.etsy.com/2010/12/08/track-every-release/)

This can be easily removed if you like.

Additionally the script will keep a log at `/var/tmp/cookbook-deploy.log`

## Setup:

First install Chef on your subversion server and drop a knife.rb, something like.

```ruby
log_level                :info
log_location             STDOUT
node_name                'chefuser'
client_key               '/path/to/subversion/.chef/chefuser.pem'
validation_client_name   'chef-validator'
validation_key           '/etc/chef/validation.pem'
chef_server_url          'http://my-chef-server.example.com:4000'
cache_type               'BasicFile'
cache_options( :path => '/path/to/subversion/.chef/checksums' )
cookbook_path [ '/var/tmp/' ]
```

Drop your client key in the path you set above so knife can validate itself to the chef server.

More info on this process is in the [Opscode wiki](http://wiki.opscode.com/display/chef/Knife#Knife-ConfiguringYourSystemForKnife)

Also, don't forget to make it r+w for the user post-commit hooks run as, probably apache or www-data.

Now update the variables at the head of the script:

`svnUser`, `svnPass`, `svnRepo`, `emailDom`, `mailServer`, `knifeConfig`, `mailFrom`, `gServer`, `gPort`

Then add something like this to you post-commit hook:
```
export HOME=/whatever/svnuser/path
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
/usr/bin/python /path/to/subversion/hooks/upload-chef-cookbook-post-commit-hook.py "$REPOS" "$REV" || exit 1
```

Make sure you set a `$PATH` and `$HOME` since the way the hook is called does not and `knife` will go bonkers.

From here you should be good to go. I had to sanatize it a bit and remove some custom functions for my environment so you may need to toggle this script a bit.


## TODO:
* Foodcritic (Y U CAN ONLY USE RUBY 1.9.3?)
* Enforce Cookbook Version bumps.
