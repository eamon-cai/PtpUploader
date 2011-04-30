from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import re;
import subprocess;

class MediaInfo:
	# removePathFromCompleteName: this part will be removed from the path listed at "Complete Name". If removePathFromCompleteName is empty then it will be left as it is.
	def __init__(self, logger, path, removePathFromCompleteName):
		self.Path = path
		self.RemovePathFromCompleteName = removePathFromCompleteName
		self.FormattedMediaInfo = ""
		self.DurationInSec = None
		self.Container = ""
		self.Codec = ""
		self.Width = 0
		self.Height = 0
		
		self.__ParseMediaInfo( logger )
		self.__ValidateParsedMediaInfo()

	# Returns with the media info.
	@staticmethod
	def ReadMediaInfo(logger, path):
		logger.info( "Reading media info from '%s'." % path );
		
		args = [ Settings.MediaInfoPath, path ];
		proc = subprocess.Popen( args, stdout = subprocess.PIPE );
		stdout, stderr = proc.communicate();
		errorCode = proc.wait();
		if errorCode != 0:
			raise PtpUploaderException( "Process execution '%s' returned with error code '%s'." % ( args, errorCode ) );			
		
		return stdout.decode( "utf-8", "ignore" );
	
	# removePathFromCompleteName: see MediaInfo's constructor
	# keepOnlyTheFirstVob: there is no point of making MediaInfo for all VOBs, so if this is true then only first VOB will be parsed.
	# Returns with the media infos for all files in videoFiles. If keepOnlyTheFirstVob is true, then returned list may not have the same length as videoFiles.
	@staticmethod
	def ReadAndParseMediaInfos(logger, videoFiles, removePathFromCompleteName, keepOnlyTheFirstVob = True):
		firstVobFound = False
		mediaInfos = []
		for video in videoFiles:
			# We could use MediaInfo.IsVob() after reading, but this is faster.
			if video.lower().endswith( ".vob" ) and keepOnlyTheFirstVob:
				if firstVobFound:
					continue
				else:
					firstVobFound = True

			mediaInfo = MediaInfo( logger, video, removePathFromCompleteName )
			mediaInfos.append( mediaInfo )
			
		return mediaInfos

	@staticmethod
	def __ParseSize(mediaPropertyValue):
		mediaPropertyValue = mediaPropertyValue.replace( "pixels", "" );
		mediaPropertyValue = mediaPropertyValue.replace( " ", "" ); # Resolution may contain space, so remove. Eg.: 1 280
		return int( mediaPropertyValue );

	# Matches duration in the following format. All units and spaces are optional.
	# 1h 2mn 3s
	@staticmethod
	def __GetDurationInSec(duration):
		# Nice regular expression. :)
		# r means to do not unescape the string
		# ?: means to do not store that group capture
		match = re.match( r"(?:(\d+)h\s?)?(?:(\d+)mn\s?)?(?:(\d+)s\s?)?" , duration )
		if not match:
			return 0;
	
		duration = 0;
		if match.group( 1 ):
			duration += int( match.group( 1 ) ) * 60 * 60;
		if match.group( 2 ):
			duration += int( match.group( 2 ) ) * 60;
		if match.group( 3 ):
			duration += int( match.group( 3 ) );
		
		return duration;		

	def __MakeCompleteNameRelative(self, path):
		if len( self.RemovePathFromCompleteName ) > 0:
			removePathFromCompleteName = self.RemovePathFromCompleteName.replace( "\\", "/" )
			if not removePathFromCompleteName.endswith( "/" ):
				removePathFromCompleteName += "/"
	
			path = path.replace( "\\", "/" )
			path = path.replace( removePathFromCompleteName, "" )
			
		return path

	def __ParseMediaInfo(self, logger):
		mediaInfoText = MediaInfo.ReadMediaInfo( logger, self.Path );

		section = "";
		for line in mediaInfoText.splitlines():
			if line.find( ":" ) == -1:
				if len( line ) > 0:
					section = line;
					line = "[b]" + line + "[/b]";
			else:
				mediaPropertyName, separator, mediaPropertyValue = line.partition( ": " )
				originalMediaPropertyName = mediaPropertyName
				mediaPropertyName = mediaPropertyName.strip()

				if section == "General":
					if mediaPropertyName == "Complete name":
						line = originalMediaPropertyName + separator + self.__MakeCompleteNameRelative( mediaPropertyValue )
					elif mediaPropertyName == "Format":
						self.Container = mediaPropertyValue.lower();
					elif mediaPropertyName == "Duration":
						self.DurationInSec = MediaInfo.__GetDurationInSec( mediaPropertyValue );
				elif section == "Video":
					if mediaPropertyName == "Codec ID":
						self.Codec = mediaPropertyValue.lower();
					elif mediaPropertyName == "Width":
						self.Width = MediaInfo.__ParseSize( mediaPropertyValue );
					elif mediaPropertyName == "Height":
						self.Height = MediaInfo.__ParseSize( mediaPropertyValue );

			self.FormattedMediaInfo += line + "\n";
			
	def __ValidateParsedMediaInfo(self):
		# We don't check codec because it not present for VOBs.
		
		if self.DurationInSec is None:
			raise PtpUploaderException( "MediaInfo couldn't parse the file '%s'." % self.Path )

		if self.DurationInSec <= 0:
			raise PtpUploaderException( "MediaInfo returned with invalid duration: '%s'." % self.DurationInSec )

		if len( self.Container ) <= 0:
			raise PtpUploaderException( "MediaInfo returned with no container." )

		if self.Width <= 0:
			raise PtpUploaderException( "MediaInfo returned with invalid width: '%s'." % self.Width )

		if self.Height <= 0:
			raise PtpUploaderException( "MediaInfo returned with invalid height: '%s'." % self.Height )
			
	def IsAvi(self):
		return self.Container == "avi";

	def IsMkv(self):
		return self.Container == "matroska";

	def IsVob(self):
		return self.Container == "mpeg-ps";

	def IsDivx(self):
		return self.Codec == "dx50";
	
	def IsXvid(self):
		return self.Codec == "xvid";

	def IsX264(self):
		return self.Codec == "v_mpeg4/iso/avc";