# Danbooru/e621 tag lists archive 
for use in tag autocomplete extensions, and some other stuff

This repo contains mainly through a script created tag lists of Danbooru and e621.
The script with which the tag lists are made can be found here: https://github.com/DraconicDragon/danbooru-e621-tag-list-processor

There are README files in the tag-lists folders that should explain the file naming etc

**Every month**, on the first day of that month, a GitHub actions workflow runs and uploads gathered tag lists as artifact;  
while **every three months** (1, 4, 7, 10) that workflow commits and pushes the tag list update to the repo. (Reason is to keep the repo size low, maybe I should bother uploading these to HuggingFace instead at some point)

quicklinks
- [Danbooru E621 Merged Tag Lists](tag-lists/danbooru_e621_merged/README.MD)
- [Danbooru Tag Lists](tag-lists/danbooru/README.md)
- [E621 Tag Lists](tag-lists/e621/README.md)

- [raw stuff](raw/README.md)

### If you are a developer

... looking to use these in some way, please don't rely on the merged list - it is not very future proof or scalable. Instead I recommend and hope that you will implement a way to load multiple CSV files in your project. The merging method used by my script came to existence purely because of convenience - it worked with existing autocomplete extensions with no or only minor issues (which didnt impact functionality) and did not require third parties to write extra code for it.

<details><summary>Extra notes about how bad the current merging method is</summary>
The current merging method simply increases E621's category count by 7, which is in danboru's invalid region (above 5/6), so they don't collide with each other. This is not future proof because if danbooru decides to add 2-3 more categories, they will collide - updating the merged list would then require an update to the autocomplete extensions using the merged list. The same thing is about scalability - If there is a new service that also has a similar structure/tags (maybe gelbooru <sub><sub>gelbooru's api responses are garbaw, but i havent dug further into it</sub></sub>, rule34 or bbooru?) then how would that be added to the merged list? Yes categories can just be increased again, but this is all hardcoded and shouldn't be. I did think of a way like adding a "service" column that has a string like "danbooru,e621" or just "danbooru" and "e621" (depending on tag, more robust if category numbers are different and same numbers mean different things) but at that point writing the code to support this would be just as much as supporting multiple files loaded (probably not but im also kind of trying to convince whichever dev might be reading this). And also at that point having a single file to load for tags the user probably doesnt want anyway might be suboptimal either way.
  
TLDR: Just don't write your code around the merged list and in best case support loading multiple CSV files.
</details>
