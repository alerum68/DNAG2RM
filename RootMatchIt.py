import hashlib
import logging
import os
import re
import sqlite3
import traceback
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler
from tqdm import tqdm
from sqlalchemy import BigInteger, Column, create_engine, Float, func, ForeignKey, Index, Integer, String, text, \
    inspect, Text, UniqueConstraint
from sqlalchemy.event import listen
from sqlalchemy.exc import MultipleResultsFound, SQLAlchemyError
from sqlalchemy.orm import declarative_base, relationship, Session, sessionmaker
from sqlalchemy.schema import CreateIndex

# Switches
limit = 0
# Ancestry
ancestry_matchgroups = 1
ancestry_matchtrees = 1
ancestry_treedata = 1
ancestry_icw = 1
ancestry_ancestorcouple = 1
ancestry_matchethnicity = 1
# FTDNA
ftdna_matches2 = 0
ftdna_chromo2 = 0
ftdna_icw2 = 0
dg_tree = 0
dg_individual = 0
# MyHeritage
mh_match = 0
mh_ancestors = 0
mh_chromo = 0
mh_icw = 0
mh_tree = 0

Base = declarative_base()
RM_Base = declarative_base()


class ChildTable(RM_Base):
    # Define RootsMagic ChildTable
    __tablename__ = 'ChildTable'

    RecID = Column(Integer, primary_key=True)
    ChildID = Column(Integer)
    FamilyID = Column(Integer)
    RelFather = Column(Integer)
    RelMother = Column(Integer)
    ChildOrder = Column(Integer)
    IsPrivate = Column(Integer)
    ProofFather = Column(Integer)
    ProofMother = Column(Integer)
    Note = Column(Text)
    UTCModDate = Column(Float)

    # Define indices for ChildTable

    Index('idxChildOrder', ChildOrder)
    Index('idxChildID', ChildID)
    Index('idxChildFamilyID', FamilyID)


class DNATable(RM_Base):
    # Define RootsMagic DNATable
    __tablename__ = 'DNATable'

    RecID = Column(Integer, primary_key=True)
    ID1 = Column(Integer)
    ID2 = Column(Integer)
    Label1 = Column(Text)
    Label2 = Column(Text)
    DNAProvider = Column(Integer)
    SharedCM = Column(Float)
    SharedPercent = Column(Float)
    LargeSeg = Column(Float)
    SharedSegs = Column(Integer)
    Date = Column(Text)
    Relate1 = Column(Integer)
    Relate2 = Column(Integer)
    CommonAnc = Column(Integer)
    CommonAncType = Column(Integer)
    Verified = Column(Integer)
    Note = Column(Text)
    UTCModDate = Column(Float)

    # Define indices for DNATable
    idxDnaId2 = Index('idxDnaId2', ID2)
    idxDnaId1 = Index('idxDnaId1', ID1)


class EventTable(RM_Base):
    # Define RootsMagic EventTable
    __tablename__ = 'EventTable'
    EventID = Column(Integer, primary_key=True)
    EventType = Column(Integer)
    OwnerType = Column(Integer)
    OwnerID = Column(Integer)
    FamilyID = Column(Integer)
    PlaceID = Column(Integer)
    SiteID = Column(Integer)
    Date = Column(Text)
    SortDate = Column(BigInteger)
    IsPrimary = Column(Integer)
    IsPrivate = Column(Integer)
    Proof = Column(Integer)
    Status = Column(Integer)
    Sentence = Column(Text)
    Details = Column(Text)
    Note = Column(Text)
    UTCModDate = Column(Float)

    # Define indices for EventTable
    idxOwnerEvent = Index('idxOwnerEvent', OwnerID, EventType)
    idxOwnerDate = Index('idxOwnerDate', OwnerID, SortDate)


class FactTypeTable(RM_Base):
    # Define RootsMagic FactTypeTable
    __tablename__ = 'FactTypeTable'
    FactTypeID = Column(Integer, primary_key=True)
    OwnerType = Column(Integer)
    Name = Column(Text)
    Abbrev = Column(Text)
    GedcomTag = Column(Text)
    UseValue = Column(Integer)
    UseDate = Column(Integer)
    UsePlace = Column(Integer)
    Sentence = Column(Text)
    Flags = Column(Integer)
    UTCModDate = Column(Float)

    # Define indices for FactTypeTable
    idxFactTypeName = Index('idxFactTypeName', Name)
    idxFactTypeAbbrev = Index('idxFactTypeAbbrev', Abbrev)
    idxFactTypeGedcomTag = Index('idxFactTypeGedcomTag', GedcomTag)


class FamilyTable(RM_Base):
    # Define RootsMagic FamilyTable
    __tablename__ = 'FamilyTable'
    FamilyID = Column(Integer, primary_key=True)
    FatherID = Column(Integer)
    MotherID = Column(Integer)
    ChildID = Column(Integer)
    HusbOrder = Column(Integer)
    WifeOrder = Column(Integer)
    IsPrivate = Column(Integer)
    Proof = Column(Integer)
    SpouseLabel = Column(Integer)
    FatherLabel = Column(Integer)
    MotherLabel = Column(Integer)
    SpouseLabelStr = Column(Text)
    FatherLabelStr = Column(Text)
    MotherLabelStr = Column(Text)
    Note = Column(Text)
    UTCModDate = Column(Float)

    # Define indices for FamilyTable
    idxFamilyMotherID = Index('idxFamilyMotherID', MotherID)
    idxFamilyFatherID = Index('idxFamilyFatherID', FatherID)


class GroupTable(RM_Base):
    # Define RootsMagic GroupTable
    __tablename__ = 'GroupTable'
    RecID = Column(Integer, primary_key=True)
    GroupID = Column(Integer)
    StartID = Column(Integer)
    EndID = Column(Integer)
    UTCModDate = Column(Float)


class NameTable(RM_Base):
    # Define RootsMagic NameTable
    __tablename__ = 'NameTable'
    NameID = Column(Integer, primary_key=True)
    OwnerID = Column(Integer)
    Surname = Column(Text)
    Given = Column(Text)
    Prefix = Column(Text)
    Suffix = Column(Text)
    Nickname = Column(Text)
    NameType = Column(Integer)
    Date = Column(Text)
    SortDate = Column(Integer)
    IsPrimary = Column(Integer)
    IsPrivate = Column(Integer)
    Proof = Column(Integer)
    Sentence = Column(Text)
    Note = Column(Text)
    BirthYear = Column(Integer)
    DeathYear = Column(Integer)
    Display = Column(Integer)
    Language = Column(Text)
    UTCModDate = Column(Float)
    SurnameMP = Column(Text)
    GivenMP = Column(Text)
    NicknameMP = Column(Text)

    # Define indices for NameTable
    idxSurnameGiven = Index('idxSurnameGiven', Surname, Given, BirthYear, DeathYear)
    idxSurnameGivenMP = Index('idxSurnameGivenMP', SurnameMP, GivenMP, BirthYear, DeathYear)
    idxNamePrimary = Index('idxNamePrimary', IsPrimary)
    idxGivenMP = Index('idxGivenMP', GivenMP)
    idxNameOwnerID = Index('idxNameOwnerID', OwnerID)
    idxGiven = Index('idxGiven', Given)
    idxSurname = Index('idxSurname', Surname)
    idxSurnameMP = Index('idxSurnameMP', SurnameMP)


class PersonTable(RM_Base):
    # Define RootsMagic PersonTable
    __tablename__ = 'PersonTable'
    PersonID = Column(Integer, primary_key=True)
    UniqueID = Column(Text)
    Sex = Column(Integer)
    ParentID = Column(Integer)
    SpouseID = Column(Integer)
    Color = Column(Integer)
    Color1 = Column(Integer)
    Color2 = Column(Integer)
    Color3 = Column(Integer)
    Color4 = Column(Integer)
    Color5 = Column(Integer)
    Color6 = Column(Integer)
    Color7 = Column(Integer)
    Color8 = Column(Integer)
    Color9 = Column(Integer)
    Relate1 = Column(Integer)
    Relate2 = Column(Integer)
    Flags = Column(Integer)
    Living = Column(Integer)
    IsPrivate = Column(Integer)
    Proof = Column(Integer)
    Bookmark = Column(Integer)
    Note = Column(Text)
    UTCModDate = Column(Float)


class PlaceTable(RM_Base):
    # Define RootsMagic PlaceTable
    __tablename__ = 'PlaceTable'
    PlaceID = Column(Integer, primary_key=True)
    PlaceType = Column(Integer)
    Name = Column(Text)
    Abbrev = Column(Text)
    Normalized = Column(Text)
    Latitude = Column(Integer)
    Longitude = Column(Integer)
    LatLongExact = Column(Integer)
    MasterID = Column(Integer)
    Note = Column(Text)
    Reverse = Column(Text)
    fsID = Column(Integer)
    anID = Column(Integer)
    UTCModDate = Column(Float)

    # Define indices for PlaceTable
    idxPlaceName = Index('idxPlaceName', Name)
    idxPlaceAbbrev = Index('idxPlaceAbbrev', Abbrev)
    idxReversePlaceName = Index('idxReversePlaceName', Reverse)


class URLTable(RM_Base):
    # Define RootsMagic URLTable
    __tablename__ = 'URLTable'
    LinkID = Column(Integer, primary_key=True)
    OwnerType = Column(Integer)
    OwnerID = Column(Integer)
    LinkType = Column(Integer)
    Name = Column(Text)
    URL = Column(Text)
    Note = Column(Text)
    UTCModDate = Column(Float)

    # Define indices for URLTable
    idxUrlOwnerID = Index('idxUrlOwnerID', OwnerID)
    idxUrlOwnerType = Index('idxUrlOwnerType', OwnerType)


Ancestry_Base = declarative_base()


class AncestryAncestorCouple(Ancestry_Base):
    __tablename__ = "AncestryAncestorCouple"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    TestGuid = Column(String(36))
    MatchGuid = Column(String(36), ForeignKey("Ancestry_matchGroups.matchGuid"))
    FatherAmtGid = Column(String)
    FatherBigTreeGid = Column(String)
    FatherKinshipPathToSampleId = Column(String)
    FatherKinshipPathFromSampleToMatch = Column(String)
    FatherPotential = Column(Integer)
    FatherInMatchTree = Column(Integer)
    FatherInBestContributorTree = Column(Integer)
    FatherDisplayName = Column(String)
    FatherBirthYear = Column(String)
    FatherDeathYear = Column(String)
    FatherIsMale = Column(Integer)
    FatherNotFound = Column(Integer)
    FatherVeiled = Column(Integer)
    FatherRelationshipToSampleId = Column(String)
    FatherRelationshipFromSampleToMatch = Column(String)
    MotherAmtGid = Column(String)
    MotherBigTreeGid = Column(String)
    MotherKinshipPathToSampleId = Column(String)
    MotherKinshipPathFromSampleToMatch = Column(String)
    MotherPotential = Column(Integer)
    MotherInMatchTree = Column(Integer)
    MotherInBestContributorTree = Column(Integer)
    MotherDisplayName = Column(String)
    MotherBirthYear = Column(String)
    MotherDeathYear = Column(String)
    MotherIsFemale = Column(Integer)
    MotherNotFound = Column(Integer)
    MotherVeiled = Column(Integer)
    MotherRelationshipToSampleId = Column(String)
    MotherRelationshipFromSampleToMatch = Column(String)
    group = relationship("Ancestry_matchGroups", back_populates="ancestor_couples")
    __table_args__ = (
        Index("IDX_AncestryAncestorCouple", "TestGuid", "MatchGuid", unique=True),
    )


class Ancestry_ICW(Ancestry_Base):
    __tablename__ = "Ancestry_ICW"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    matchid = Column(String, ForeignKey("Ancestry_matchGroups.matchGuid"))
    icwid = Column(String)
    created_date = Column(String)
    sharedCentimorgans = Column(Float)
    confidence = Column(Float)
    meiosis = Column(Integer)
    numSharedSegments = Column(Integer)
    group = relationship("Ancestry_matchGroups", back_populates="icw_matches")
    __table_args__ = Index("IDX_Ancestry_ICW2", "icwid", "matchid", unique=True), Index(
        "IDX_Ancestry_ICW", "matchid", "icwid", unique=True
    )


class Ancestry_Ethnicity(Ancestry_Base):
    __tablename__ = "Ancestry_Ethnicity"
    code = Column(String, primary_key=True, nullable=False)
    value = Column(String)


class Ancestry_matchEthnicity(Ancestry_Base):
    __tablename__ = "Ancestry_matchEthnicity"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    matchGuid = Column(String, ForeignKey("Ancestry_matchGroups.matchGuid"))
    ethnicregions = Column(String)
    ethnictraceregions = Column(String)
    created_date = Column(String)
    percent = Column(Integer)
    version = Column(Integer)
    group = relationship("Ancestry_matchGroups", back_populates="match_ethnicity")
    __table_args__ = (Index("IDX_Ancestry_matchEthnicity", "matchGuid", unique=True),)


class Ancestry_matchGroups(Ancestry_Base):
    __tablename__ = "Ancestry_matchGroups"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    testGuid = Column(String(36))
    matchGuid = Column(String(36), unique=True)
    matchTestDisplayName = Column(String)
    matchTestAdminDisplayName = Column(String)
    matchTreeNodeCount = Column(Integer)
    groupName = Column(String)
    confidence = Column(Float)
    sharedCentimorgans = Column(Float)
    fetchedSegmentInfo = Column(Integer)
    totalSharedCentimorgans = Column(Float)
    longestSegmentCentimorgans = Column(Float)
    sharedSegment = Column(Integer)
    lastLoggedInDate = Column(String)
    starred = Column(String)
    viewed = Column(String)
    matchTreeIsPrivate = Column(String)
    hasHint = Column(String)
    note = Column(String)
    userPhoto = Column(String)
    matchTreeId = Column(String)
    treeId = Column(String)
    matchMemberSinceYear = Column(String)
    created_date = Column(String)
    icwRunDate = Column(String)
    treeRunDate = Column(String)
    loginUsername = Column(String)
    sync = Column(String)
    matchTestAdminUcdmId = Column(String)
    GF_Sync = Column(String)
    paternal = Column(Integer)
    maternal = Column(Integer)
    subjectGender = Column(String)
    meiosisValue = Column(String)
    parentCluster = Column(String)
    matchRunDate = Column(String)
    match_trees = relationship(
        "Ancestry_matchTrees",
        primaryjoin="Ancestry_matchGroups.matchGuid == Ancestry_matchTrees.matchid",
        back_populates="group",
    )
    tree_data = relationship(
        "Ancestry_TreeData",
        primaryjoin="Ancestry_matchGroups.matchGuid == foreign(Ancestry_TreeData.TestGuid)",
        back_populates="group",
    )
    profile = relationship(
        "Ancestry_Profiles",
        primaryjoin="Ancestry_matchGroups.testGuid == foreign(Ancestry_Profiles.guid)",
        back_populates="group",
    )
    icw_matches = relationship("Ancestry_ICW", back_populates="group")
    match_ethnicity = relationship("Ancestry_matchEthnicity", back_populates="group")
    ancestor_couples = relationship("AncestryAncestorCouple", back_populates="group")
    __table_args__ = (
        Index(
            "IDX_Ancestry_matchGroups5",
            "matchGuid",
            "testGuid",
            "sharedCentimorgans",
            "groupName",
            unique=True,
        ),
        Index(
            "IDX_Ancestry_matchGroups3",
            "testGuid",
            "matchGuid",
            "groupName",
            unique=True,
        ),
        Index("IDX_Ancestry_matchGroups", "testGuid", "matchGuid", unique=True),
        Index(
            "IDX_Ancestry_matchGroups4",
            "testGuid",
            "matchGuid",
            "sharedCentimorgans",
            unique=True,
        ),
        Index("IDX_Ancestry_matchGroups2", "matchGuid"),
    )


class Ancestry_matchTrees(Ancestry_Base):
    __tablename__ = "Ancestry_matchTrees"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    matchid = Column(String(36), ForeignKey("Ancestry_matchGroups.matchGuid"))
    surname = Column(String)
    given = Column(String)
    birthdate = Column(String)
    deathdate = Column(String)
    birthplace = Column(String)
    deathplace = Column(String)
    relid = Column(String)
    personId = Column(String)
    fatherId = Column(String)
    motherId = Column(String)
    source = Column(String)
    created_date = Column(String)
    loginUsername = Column(String)
    sync = Column(String)
    birthdt1 = Column(BigInteger)
    birthdt2 = Column(BigInteger)
    deathdt1 = Column(BigInteger)
    deathdt2 = Column(BigInteger)
    group = relationship("Ancestry_matchGroups", back_populates="match_trees")
    __table_args__ = (Index("IDX_Ancestry_matchTrees", "matchid", unique=True),)


class Ancestry_Profiles(Ancestry_Base):
    __tablename__ = "Ancestry_Profiles"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    guid = Column(String)
    name = Column(String)
    group = relationship(
        "Ancestry_matchGroups",
        primaryjoin="foreign(Ancestry_Profiles.guid) == Ancestry_matchGroups.testGuid",
        back_populates="profile",
    )
    __table_args__ = (Index("IDX_Ancestry_Profiles", "guid", unique=True),)


class Ancestry_TreeData(Ancestry_Base):
    __tablename__ = "Ancestry_TreeData"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    TestGuid = Column(String(36), ForeignKey("Ancestry_matchGroups.matchGuid"))
    TreeSize = Column(Integer)
    PublicTree = Column(Integer)
    PrivateTree = Column(Integer)
    UnlinkedTree = Column(Integer)
    TreeId = Column(String)
    NoTrees = Column(Integer)
    TreeUnavailable = Column(Integer)
    group = relationship(
        "Ancestry_matchGroups",
        primaryjoin="foreign(Ancestry_TreeData.TestGuid) == Ancestry_matchGroups.matchGuid",
        back_populates="tree_data",
    )
    __table_args__ = (Index("IDX_Ancestry_TreeData", "TestGuid", unique=True),)


FTDNA_Base = declarative_base()


class DGTree(FTDNA_Base):
    __tablename__ = "DGTree"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    treeid = Column(String)
    treeurl = Column(String)
    basePersonId = Column(String)
    CreateDate = Column(BigInteger)
    UpdateDate = Column(BigInteger)
    matchID = Column(String)
    source = Column(String)
    __table_args__ = Index("IDX_DGTreeSource", "source"), Index("IDX_DGTreeID", "Id")


class FTDNA_Chromo2(FTDNA_Base):
    __tablename__ = "FTDNA_Chromo2"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    eKit1 = Column(String)
    eKit2 = Column(String)
    chromosome = Column(Integer)
    cmfloat = Column(Float)
    p1 = Column(Integer)
    p2 = Column(Integer)
    snpsI = Column(Integer)
    created_date = Column(String)
    GF_Sync = Column(String)
    __table_args__ = (
        Index("IDX_FTDNA_Chromo12", "eKit1"),
        Index("IDX_FTDNA_ChromoB2", "eKit1", "eKit2"),
        Index("IDX_FTDNA_Chromo22", "eKit2"),
    )


class FTDNA_ICW2(FTDNA_Base):
    __tablename__ = "FTDNA_ICW2"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    eKitKit = Column(String)
    eKitMatch1 = Column(String)
    eKitMatch2 = Column(String)
    created_date = Column(String)
    GF_Sync = Column(String)
    __table_args__ = (
        Index("IDX_FTDNA_ICW_RRI2", "eKitKit", "eKitMatch1", "eKitMatch2"),
        Index("IDX_FTDNA_ICW12", "eKitKit"),
        Index("IDX_FTDNA_ICW_RI2", "eKitKit", "eKitMatch2"),
        Index("IDX_FTDNA_ICW32", "eKitMatch2"),
        Index("IDX_FTDNA_ICW22", "eKitMatch1"),
        Index("IDX_FTDNA_ICW_RR2", "eKitKit", "eKitMatch1"),
    )


class FTDNA_Matches2(FTDNA_Base):
    __tablename__ = "FTDNA_Matches2"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    eKit1 = Column(String)
    eKit2 = Column(String)
    Name = Column(String)
    MatchPersonName = Column(String)
    Prefix = Column(String)
    FirstName = Column(String)
    MiddleName = Column(String)
    LastName = Column(String)
    Suffix = Column(String)
    Email = Column(String)
    HasFamilyTree = Column(String)
    ThirdParty = Column(String)
    Note = Column(String)
    Female = Column(String)
    contactId = Column(String)
    AboutMe = Column(String)
    PaternalAncestorName = Column(String)
    MaternalAncestorName = Column(String)
    strRbdate = Column(String)
    Relationship = Column(String)
    strRelationshipRange = Column(String)
    strSuggestedRelationship = Column(String)
    strRelationshipName = Column(String)
    totalCM = Column(String)
    userSurnames = Column(String)
    longestCentimorgans = Column(String)
    ydnaMarkers = Column(String)
    mtDNAMarkers = Column(String)
    yHaplo = Column(String)
    mtHaplo = Column(String)
    isxMatch = Column(String)
    ffBack = Column(String)
    bucketType = Column(String)
    nRownum = Column(String)
    familyTreeUrl = Column(String)
    created_date = Column(String)
    icw_date = Column(BigInteger)
    icw_tree = Column(BigInteger)
    totalCMf = Column(Float)
    longestCentimorgansf = Column(Float)
    GF_Sync = Column(String)


class DGIndividual(FTDNA_Base):
    __tablename__ = "DGIndividual"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    treeid = Column(Integer)
    matchid = Column(String)
    surname = Column(String)
    given = Column(String)
    birthdate = Column(String)
    deathdate = Column(String)
    birthplace = Column(String)
    deathplace = Column(String)
    sex = Column(String)
    relid = Column(String)
    personId = Column(String)
    fatherId = Column(String)
    motherId = Column(String)
    spouseId = Column(String)
    source = Column(String)
    created_date = Column(String)
    birthdt1 = Column(BigInteger)
    birthdt2 = Column(BigInteger)
    deathdt1 = Column(BigInteger)
    deathdt2 = Column(BigInteger)
    __table_args__ = Index("IDX_DGIndividualTM", "treeid", "matchid"), Index(
        "IDX_DGIndividualSM", "source", "matchid"
    )


class DNAKit(FTDNA_Base):
    __tablename__ = "DNA_Kits"
    company = Column(String)
    guid = Column(String, primary_key=True)
    name = Column(String)


MH_Base = declarative_base()


class MH_Ancestors(MH_Base):
    __tablename__ = "MH_Ancestors"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    TreeId = Column(Integer)
    matchid = Column(String)
    surname = Column(String)
    given = Column(String)
    birthdate = Column(String)
    deathdate = Column(String)
    birthplace = Column(String)
    deathplace = Column(String)
    relid = Column(String)
    personId = Column(String)
    fatherId = Column(String)
    motherId = Column(String)
    gender = Column(String)
    dnaLink = Column(String)
    __table_args__ = Index("IDX_MH_Ancestors", "TreeId"), Index(
        "IDX_MH_Ancestors2", "matchid"
    )


class MH_Chromo(MH_Base):
    __tablename__ = "MH_Chromo"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    guid = Column(String)
    guid1 = Column(String)
    guid2 = Column(String)
    chromosome = Column(Integer)
    cm = Column(Float)
    start = Column(Integer)
    end = Column(Integer)
    snps = Column(Integer)
    startrs = Column(String)
    endrs = Column(String)
    GF_Sync = Column(String)
    __table_args__ = (
        UniqueConstraint("guid", "chromosome", "start", name="IDX_MH_Chromo"),
    )


class MH_ICW(MH_Base):
    __tablename__ = "MH_ICW"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    id1 = Column(String)
    id2 = Column(String)
    totalCM = Column(Float)
    percent_shared = Column(Float)
    num_segments = Column(Integer)
    triTotalCM = Column(Float)
    triSegments = Column(Integer)
    GF_Sync = Column(String)
    __table_args__ = UniqueConstraint(
        "id2", "id1", name="IDX_MH_ICW2"
    ), UniqueConstraint("id1", "id2", name="IDX_MH_ICW1")


class MH_Match(MH_Base):
    __tablename__ = "MH_Match"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    kitId = Column(Integer)
    guid = Column(String, unique=True)
    name = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    age = Column(String)
    birth_place = Column(String)
    gender = Column(String)
    country = Column(String)
    creatorid = Column(String)
    contact = Column(String)
    manager = Column(String)
    contact_manager = Column(String)
    status = Column(String)
    estimated_relationship = Column(String)
    totalCM = Column(Float)
    percent_shared = Column(Float)
    num_segments = Column(Integer)
    largestCM = Column(Float)
    has_tree = Column(Integer)
    tree_size = Column(Integer)
    tree_url = Column(String)
    person_url = Column(String)
    smart_matches = Column(Integer)
    shared_surnames = Column(String)
    surnames = Column(String)
    notes = Column(String)
    CreatedDate = Column(String)
    icwRunDate = Column(String)
    icwcMlow = Column(Float)
    triagRunDate = Column(String)
    treeRunDate = Column(String)
    chromoRunDate = Column(String)
    gmUploadDate = Column(String)
    testid = Column(String)
    matchid = Column(String)
    GF_Sync = Column(String)
    __table_args__ = (Index("IDX_MH_MATCH", "guid"),)


class MH_Tree(MH_Base):
    __tablename__ = "MH_Tree"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    treeurl = Column(String, unique=True)
    created_date = Column(String)
    updated_date = Column(String)
    __table_args__ = (UniqueConstraint("treeurl", name="IDX_MH_Tree"),)


ancestry_base = Ancestry_Base()
ftdna_base = FTDNA_Base()
mh_base = MH_Base()
rm_base = RM_Base()


def setup_logging():
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.DEBUG)
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        formatted_datetime = datetime.now().strftime("(%Y-%m-%d, %H:%M:%S)")
        file_handler_error = logging.FileHandler(
            os.path.join(log_dir, "DG2RM2_error.log"), encoding="utf-8"
        )
        file_handler_error.setLevel(logging.WARNING)
        file_handler_error.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(file_handler_error)
        file_handler_info = RotatingFileHandler(
            os.path.join(log_dir, "DG2RM.log"),
            maxBytes=1000000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler_info.setLevel(logging.INFO)
        file_handler_info.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(file_handler_info)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(console_handler)
        root_logger.critical(f"\n\n Start of run - {formatted_datetime} \n")


def init_db(database_url):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    dg_session = session()
    rm_session = session()
    return dg_session, rm_session


def rmnocase_collation(str1, str2):
    return (str1.lower() > str2.lower()) - (str1.lower() < str2.lower())


def add_collation(dbapi_conn, _):
    dbapi_conn.create_collation("RMNOCASE", rmnocase_collation)


def find_database_paths():
    db_directory = ".\\db"
    dg_db_file = None
    rm_db_file = None
    if os.path.exists(db_directory):
        files = os.listdir(db_directory)
        for file in files:
            if file.endswith(".db"):
                dg_db_file = os.path.join(db_directory, file)
            elif file.endswith(".rmtree"):
                rm_db_file = os.path.join(db_directory, file)
    if not dg_db_file or not rm_db_file:
        print("No database files found in ./db directory.")
        dg_db_path = input("Enter the path to the DNAGedcom database: ").strip()
        rm_db_path = input("Enter the path to the RootsMagic database: ").strip()
    else:
        dg_db_path = dg_db_file
        rm_db_path = rm_db_file
    return dg_db_path, rm_db_path


def connect_to_db(db_path, db_name=None):
    try:
        conn = sqlite3.connect(db_path)
        if db_name == "RootsMagic":
            conn.create_collation(
                "RMNOCASE",
                lambda x, y: (x.lower() > y.lower()) - (x.lower() < y.lower()),
            )
        logging.info(f"Connected to {db_name or 'database'} database at: {db_path}")
        return conn
    except sqlite3.Error as s3_e:
        logging.error(f"Error connecting to {db_name or 'database'} database: {s3_e}")
        return None


def connect_to_db_sqlalchemy(dg_db_path, rm_db_path):
    try:
        dg_engine = create_engine(f"sqlite:///{dg_db_path}")
        dg_bind = sessionmaker(bind=dg_engine)
        dg_session = dg_bind()
        logging.info(
            f"Connected to DNAGedcom database at: {dg_db_path} using SQLAlchemy"
        )
        rm_engine = create_engine(f"sqlite:///{rm_db_path}")
        listen(rm_engine, "connect", add_collation)
        rm_bind = sessionmaker(bind=rm_engine)
        rm_session = rm_bind()
        logging.info(
            f"Connected to RootsMagic database at: {rm_db_path} using SQLAlchemy"
        )
        return dg_session, dg_engine, rm_session, rm_engine
    except Exception as sa_e:
        logging.error(f"Error connecting to databases using SQLAlchemy: {sa_e}")
        return None, None, None, None


def user_kit_data(session):
    dna_kits = []
    try:
        ancestry_profiles = session.query(Ancestry_Profiles).all()
        logging.debug(f"Found {len(ancestry_profiles)} entries in Ancestry_Profiles.")
        dna_kits.extend(
            [
                (
                    2,
                    profile.guid,
                    *(
                        profile.name.rsplit(" ", 1)
                        if " " in profile.name
                        else (profile.name, "")
                    ),
                )
                for profile in ancestry_profiles
            ]
        )
        dna_kits_query = (
            session.query(DNAKit)
            .filter(DNAKit.company.in_(["FTDNA", "MyHeritage"]))
            .all()
        )
        logging.debug(
            f"Found {len(dna_kits_query)} entries in DNA_Kits for FTDNA or MyHeritage."
        )
        for kit in dna_kits_query:
            guid = kit.guid
            name = kit.name
            if kit.company == "MyHeritage":
                guid = guid.replace("dnakit-", "")
                name = re.sub("\\(.*\\)", "", name).strip()
            dna_kits.append(
                (
                    5 if kit.company == "MyHeritage" else 3,
                    guid,
                    *(name.rsplit(" ", 1) if " " in name else (name, "")),
                )
            )
    except Exception as e:
        logging.error(f"Error extracting user kit data: {e}")
    return dna_kits


def prompt_user_for_kits(dna_kits):
    ancestry_kits = [kit for kit in dna_kits if kit[0] == 2]
    ftdna_kits = [kit for kit in dna_kits if kit[0] == 3]
    myheritage_kits = [kit for kit in dna_kits if kit[0] == 5]
    print("Ancestry Kits:")
    for idx, kit in enumerate(ancestry_kits, 1):
        print(f"{idx}: {kit[1]} (Name: {kit[2]} {kit[3]})")
    print("\nFamily Tree DNA (FTDNA) Kits:")
    for idx, kit in enumerate(ftdna_kits, len(ancestry_kits) + 1):
        print(f"{idx}: {kit[1]} (Name: {kit[2]} {kit[3]})")
    print("\nMyHeritage Kits :")
    for idx, kit in enumerate(
            myheritage_kits, len(ancestry_kits) + len(ftdna_kits) + 1
    ):
        print(f"{idx}: {kit[1]} (Name: {kit[2]} {kit[3]})")
    selected_indices = input(
        "Enter the numbers of the kits you want to run the script on (comma-separated), or enter company name ("
        "case-insensitive) or first letter, or press Enter for all:"
    )
    selected_kits = []
    if selected_indices.strip() == "":
        selected_kits = dna_kits
    else:
        selected_indices = [idx.strip() for idx in selected_indices.split(",")]
        for idx in selected_indices:
            if idx.isdigit():
                idx = int(idx) - 1
                if 0 <= idx < len(dna_kits):
                    selected_kits.append(dna_kits[idx])
            else:
                company_map = {
                    "a": 2,
                    "ancestry": 2,
                    "f": 3,
                    "ftdna": 3,
                    "m": 5,
                    "myheritage": 5,
                }
                company_id = company_map.get(idx.lower())
                if company_id:
                    selected_kits.extend(
                        [kit for kit in dna_kits if kit[0] == company_id]
                    )
    return selected_kits


# Set a batch limit via the Limit global variable
def batch_limit(session, table_class, filter_ids, process_func, apply_limit, batch_size=999):
    processed_data = []
    total_processed = 0

    # Break down filter_ids into batches
    for i in range(0, len(filter_ids), batch_size):
        batch_ids = filter_ids[i:i + batch_size]

        query = session.query(table_class).filter(table_class.Id.in_(batch_ids))
        if apply_limit > 0:
            query = query.limit(apply_limit - total_processed)  # Adjust limit based on already processed data

        limited_data = query.all()

        # Process each item in the limited data using the provided process function
        for item in limited_data:
            processed_data.append(process_func(item))

        total_processed += len(limited_data)

        if 0 < apply_limit <= total_processed:
            break

    return processed_data[:apply_limit] if apply_limit > 0 else processed_data


# Generate UUIDs
def generate_unique_id(*args) -> str:
    filtered_args = [str(arg) for arg in args if arg]
    unique_str = ' '.join(filtered_args)
    namespace = uuid.NAMESPACE_DNS
    unique_id = str(uuid.uuid5(namespace, unique_str))
    return unique_id


# Generate a hashed version of PersonID, FatherID, and MotherID to fix DnaGedcom ID size
def hash_id(original_id, id_mapping):
    if original_id is None:
        return None
    if original_id in id_mapping:
        return id_mapping[original_id]
    hash_object = hashlib.md5(str(original_id).encode())
    hash_hex = hash_object.hexdigest()
    hash_int = int(hash_hex[:8], 16)
    hashed_id = (hash_int % 9999999) + 100
    id_mapping[original_id] = hashed_id
    # logging.debug(f"Hashing ID: original_id={original_id}, hashed_id={hashed_id}")
    return hashed_id


# A check for duplicate records.
def check_for_duplicates(session: Session, unique_id: str, **kwargs):
    logging.getLogger('get_or_create_person')
    try:
        person = session.query(PersonTable).filter_by(UniqueID=unique_id).first()
        if person:
            for key, value in kwargs.items():
                setattr(person, key, value)
            logging.info(f"Updated existing person: {unique_id}")
        else:
            person = PersonTable(UniqueID=unique_id, **kwargs)
            session.add(person)
            logging.info(f"Created new person: {unique_id}")
        return person
    except SQLAlchemyError as dup_e:
        logging.error(f"Error in get_or_create_person for {unique_id}: {dup_e}")
        logging.error(traceback.format_exc())
        session.rollback()
        return None


# Filter results based on kits selected via select_kits function.
def filter_selected_kits(filter_session: Session, f_selected_kits):
    global ancestry_matchgroups, ancestry_matchtrees, ancestry_treedata, ancestry_icw, \
        ancestry_ancestorcouple, ancestry_matchethnicity
    global ftdna_matches2, ftdna_chromo2, ftdna_icw2, dg_tree, dg_individual
    global mh_match, mh_ancestors, mh_chromo, mh_icw, mh_tree
    logging.getLogger('filter_selected_kits')
    # logging.info("Filtering selected kits...")

    selected_guids = [kit[1] for kit in f_selected_kits]
    test_ids = {
        'Ancestry_matchGroups': [], 'Ancestry_matchTrees': [], 'Ancestry_TreeData': [],
        'Ancestry_ICW': [], 'AncestryAncestorCouple': [], 'Ancestry_matchEthnicity': [],
        'FTDNA_Matches2': [], 'FTDNA_Chromo2': [], 'FTDNA_ICW2': [],
        'DGTree': [], 'DGIndividual': [],
        'MH_Match': [], 'MH_Ancestors': [], 'MH_Chromo': [], 'MH_ICW': [], 'MH_Tree': []
    }

    try:
        # Ancestry filters
        match_guids = []
        if ancestry_matchgroups:
            ancestry_matches = filter_session.query(Ancestry_matchGroups).filter(
                Ancestry_matchGroups.testGuid.in_(selected_guids)).all()
            test_ids['Ancestry_matchGroups'] = [match.Id for match in ancestry_matches]

            # Get matchGuids for use in other Ancestry tables
            match_guids = [group.matchGuid for group in ancestry_matches]

            if ancestry_matchtrees:
                # Use both selected_guids and match_guids for ancestry_matchtrees
                guids_to_check = selected_guids + match_guids
                ancestry_matches_trees = filter_session.query(Ancestry_matchTrees).filter(
                    Ancestry_matchTrees.matchid.in_(guids_to_check)).all()
                test_ids['Ancestry_matchTrees'] = [match.Id for match in ancestry_matches_trees]

        if ancestry_treedata:
            ancestry_tree_data = filter_session.query(Ancestry_TreeData).filter(
                Ancestry_TreeData.TestGuid.in_(selected_guids)).all()
            test_ids['Ancestry_TreeData'] = [data.Id for data in ancestry_tree_data]

        if ancestry_icw:
            ancestry_icw_data = filter_session.query(Ancestry_ICW).filter(
                Ancestry_ICW.matchid.in_(match_guids)).all()
            test_ids['Ancestry_ICW'] = [icw.Id for icw in ancestry_icw_data]

        if ancestry_ancestorcouple:
            ancestry_ancestor_couple = filter_session.query(AncestryAncestorCouple).filter(
                AncestryAncestorCouple.TestGuid.in_(selected_guids)).all()
            test_ids['AncestryAncestorCouple'] = [couple.Id for couple in ancestry_ancestor_couple]

        if ancestry_matchethnicity:
            ancestry_match_ethnicity = filter_session.query(Ancestry_matchEthnicity).filter(
                Ancestry_matchEthnicity.matchGuid.in_(match_guids)).all()
            test_ids['Ancestry_matchEthnicity'] = [ethnicity.Id for ethnicity in ancestry_match_ethnicity]

        # FTDNA filters
        if ftdna_matches2:
            ftdna_matches = filter_session.query(FTDNA_Matches2).filter(
                FTDNA_Matches2.eKit1.in_(selected_guids)).all()
            test_ids['FTDNA_Matches2'] = [match.Id for match in ftdna_matches]

        if ftdna_chromo2:
            ftdna_chromo = filter_session.query(FTDNA_Chromo2).filter(
                FTDNA_Chromo2.eKit1.in_(selected_guids)).all()
            test_ids['FTDNA_Chromo2'] = [chromo.Id for chromo in ftdna_chromo]

        if ftdna_icw2:
            ftdna_icw = filter_session.query(FTDNA_ICW2).filter(
                FTDNA_ICW2.eKitKit.in_(selected_guids)).all()
            test_ids['FTDNA_ICW2'] = [icw.Id for icw in ftdna_icw]

        if dg_tree:
            dg_trees = filter_session.query(DGTree).filter(
                DGTree.matchID.in_(selected_guids)).all()
            test_ids['DGTree'] = [tree.Id for tree in dg_trees]

        if dg_individual:
            dg_individuals = filter_session.query(DGIndividual).filter(
                DGIndividual.matchid.in_(selected_guids)).all()
            test_ids['DGIndividual'] = [individual.Id for individual in dg_individuals]

        # MyHeritage filters
        if mh_match:
            mh_matches = filter_session.query(MH_Match).filter(
                MH_Match.guid.in_(selected_guids)).all()
            test_ids['MH_Match'] = [match.Id for match in mh_matches]

        if mh_ancestors:
            mh_ancestors_data = filter_session.query(MH_Ancestors).filter(
                MH_Ancestors.matchid.in_(selected_guids)).all()
            test_ids['MH_Ancestors'] = [ancestor.Id for ancestor in mh_ancestors_data]

        if mh_chromo:
            mh_chromo_data = filter_session.query(MH_Chromo).filter(
                MH_Chromo.guid.in_(selected_guids)).all()
            test_ids['MH_Chromo'] = [chromo.Id for chromo in mh_chromo_data]

        if mh_icw:
            mh_icw_data = filter_session.query(MH_ICW).filter(
                MH_ICW.id1.in_(selected_guids)).all()
            test_ids['MH_ICW'] = [icw.Id for icw in mh_icw_data]

        if mh_tree:
            mh_tree_data = filter_session.query(MH_Tree).all()
            test_ids['MH_Tree'] = [tree.Id for tree in mh_tree_data]

    except Exception as filter_e:
        logging.error(f"Error filtering selected kits: {filter_e}")
        logging.error(traceback.format_exc())
        raise

    return test_ids


# Create the DNA Kit FactType if not present.  For future integration with existing tree.
def insert_fact_type(fact_rm_session: Session):
    logging.getLogger('insert_fact_type')

    try:
        # Check if Fact Type 'DNA Kit' already exists
        fact_type = fact_rm_session.query(FactTypeTable).filter_by(Name='DNA Kit').first()

        if not fact_type:
            # Create a new Fact Type 'DNA Kit' if it doesn't exist
            new_fact_type = FactTypeTable(
                OwnerType=0,
                Name='DNA Kit',
                Abbrev='DNA Kit',
                GedcomTag='EVEN',
                UseValue=1,
                UseDate=0,
                UsePlace=0,
                Sentence='[person] had a DNA test performed. View DNA Tab in profile to view matches.',
                Flags=2147483647,
                UTCModDate=func.julianday(func.current_timestamp()) - 2415018.5,
            )
            fact_rm_session.add(new_fact_type)
            fact_rm_session.commit()
            logging.info("Fact Type 'DNA Kit' inserted into FactTypeTable.")
        else:
            # Update existing Fact Type 'DNA Kit'
            fact_type.OwnerType = 0
            fact_type.Abbrev = 'DNA Kit'
            fact_type.GedcomTag = 'EVEN'
            fact_type.UseValue = 1
            fact_type.UseDate = 0
            fact_type.UsePlace = 0
            fact_type.Sentence = '[person] had a DNA test performed. View DNA Tab in profile to view matches.'
            fact_type.Flags = 2147483647
            fact_type.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5
            fact_rm_session.commit()
            # logging.info("Fact Type 'DNA Kit' updated in FactTypeTable.")
    except Exception as e:
        logging.error(f"Error inserting or updating Fact Type 'DNA Kit' in FactTypeTable: {e}")
        logging.error(traceback.format_exc())
        fact_rm_session.rollback()
        raise
    finally:
        fact_rm_session.close()


# Import Ancestry Profiles and FTDNA and MyHeritage DNA Kits.
def import_profiles(rm_session: Session, selected_kits):
    def get_gender_input(profile_name_given, profile_name_surname, profile_guid_value):
        # Manually enter gender for each Profile or DNA Kit.
        while True:
            gender = input(f"Enter gender for kit {profile_name_given} {profile_name_surname}, "
                           f"GUID {profile_guid_value} ((M)ale, (F)emale, (U)nknown): ").strip().upper()
            if gender in ['M', 'MALE']:
                return 0
            elif gender in ['F', 'FEMALE']:
                return 1
            elif gender in ['U', 'UNKNOWN']:
                return 2
            else:
                print("Invalid input. Please enter M/Male, F/Female, or U/Unknown.")

    for kit_details in selected_kits:
        id_value, guid_value, name_given, name_surname = kit_details

        try:
            # Attempt to fetch existing person record by UniqueID
            person_record = rm_session.query(PersonTable).filter_by(UniqueID=guid_value).one_or_none()

            if person_record:
                # Use existing gender value if it is already set
                if person_record.Sex not in [0, 1]:
                    gender_value = get_gender_input(name_given, name_surname, guid_value)
                else:
                    gender_value = person_record.Sex

                # Update existing record with new gender value if needed
                if person_record.Sex != gender_value:
                    person_record.Sex = gender_value
                    person_record.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5

            else:
                gender_value = get_gender_input(name_given, name_surname, guid_value)
                person_record = PersonTable(
                    UniqueID=guid_value,
                    Color=1,
                    UTCModDate=func.julianday(func.current_timestamp()) - 2415018.5,
                    Sex=gender_value
                )
                rm_session.add(person_record)

            rm_session.commit()

            # Retrieve PersonID and process NameTable records
            person_id = person_record.PersonID
            existing_name = rm_session.query(NameTable).filter_by(OwnerID=person_id, NameType=0).first()

            if existing_name:
                # Update existing name record
                existing_name.Given = name_given
                existing_name.Surname = name_surname
                existing_name.IsPrimary = 1
            else:
                # Create a new name record in NameTable
                profile_name_table = NameTable(
                    OwnerID=person_id,
                    Given=name_given,
                    Surname=name_surname,
                    IsPrimary=1,
                    IsPrivate=0,
                    Proof=0,
                    UTCModDate=func.julianday(func.current_timestamp()) - 2415018.5,
                    SortDate=int(9223372036854775807),
                    NameType=0,
                    GivenMP=name_given,
                    SurnameMP=name_surname
                )
                rm_session.add(profile_name_table)

        except MultipleResultsFound:
            logging.error(f"Multiple records found for UniqueID: {guid_value}. "
                          f"Please check the database for duplicates.")
            logging.error(traceback.format_exc())
            rm_session.rollback()
        except Exception as e:
            logging.error(f"Error processing kit: {id_value}, GUID: {guid_value}, Name: {name_given} {name_surname}")
            logging.error(traceback.format_exc())
            logging.exception(e)
            rm_session.rollback()

    rm_session.commit()
    # logging.info("Inserted or updated selected Profiles.")


# Process Ancestry data
def process_ancestry(session: Session, filtered_ids):
    global limit
    logging.getLogger('process_ancestry')
    # logging.info("Processing Ancestry data...")

    processed_ancestry_data = []
    id_mapping = {}
    try:
        # Process Ancestry_MatchGroups data
        if ancestry_matchgroups and filtered_ids.get('Ancestry_matchGroups'):
            def process_matchgroup(mg_session, group):
                # Query Ancestry_matchTrees using matchGuid
                match_tree = mg_session.query(Ancestry_matchTrees).filter_by(matchid=group.matchGuid).first()

                # create hashed ids for PersonID, FatherID, and MotherID
                if match_tree and match_tree.personId is not None:
                    person_id = hash_id(match_tree.personId, id_mapping)
                    father_id = hash_id(match_tree.fatherId, id_mapping) if match_tree.fatherId is not None else None
                    mother_id = hash_id(match_tree.motherId, id_mapping) if match_tree.motherId is not None else None
                    color = 18
                else:
                    # If no match_tree is found, generate a default person_id using matchGuid and set color to 27
                    person_id = hash_id(group.matchGuid, id_mapping)
                    father_id = None
                    mother_id = None
                    color = 27

                # Extract name and sex information
                name = group.matchTestDisplayName
                given, surname = (name.split()[0], name.split()[-1]) if len(name.split()) > 1 else (name, "")

                subject_gender = group.subjectGender
                sex = 1 if subject_gender == 'F' else 0 if subject_gender == 'M' else 2  # Default or unknown value

                return {
                    'source': 'process_matchgroup',
                    'DNAProvider': 2,
                    'PersonID': person_id,
                    'FatherID': father_id,
                    'MotherID': mother_id,
                    'unique_id': group.matchGuid,
                    'matchGuid': group.matchGuid,
                    'testGuid': group.testGuid,
                    'sex': sex,
                    'color': color,
                    'matchTestDisplayName': group.matchTestDisplayName,
                    'Given': given,
                    'Surname': surname,
                    'groupName': group.groupName,
                    'confidence': group.confidence,
                    'sharedCM': group.sharedCentimorgans,
                    'SharedSegs': group.sharedSegment,
                    'starred': group.starred,
                    'note': group.note,
                    'matchTreeId': group.matchTreeId,
                    'treeId': group.treeId,
                    'icwRunDate': group.icwRunDate,
                    'treeRunDate': group.treeRunDate,
                    'matchRunDate': group.matchRunDate,
                    'paternal': group.paternal,
                    'maternal': group.maternal,
                    'subjectGender': group.subjectGender,
                    'meiosisValue': group.meiosisValue,
                    'parentCluster': group.parentCluster,
                    'IsPrimary': 1,
                    'NameType': 0,
                }

            match_groups = batch_limit(
                session, Ancestry_matchGroups, filtered_ids.get('Ancestry_matchGroups', []),
                lambda group: process_matchgroup(session, group), limit
            )

            id_mapping = {group['unique_id']: group for group in match_groups}
            processed_ancestry_data.extend(match_groups or [])

        # Process Ancestry_MatchTrees data
        if ancestry_matchtrees and filtered_ids.get('Ancestry_matchTrees'):
            def process_matchtree(tree, person_data=None):
                try:
                    data_source = person_data if person_data else tree

                    # Get IDs
                    person_id = hash_id(data_source.personId, id_mapping)
                    father_id = hash_id(data_source.fatherId, id_mapping) if data_source.fatherId is not None else None
                    mother_id = hash_id(data_source.motherId, id_mapping) if data_source.motherId is not None else None

                    # Determine gender
                    sex_value = 2
                    if data_source.personId is not None:
                        father_match = session.query(Ancestry_matchTrees).filter(
                            Ancestry_matchTrees.fatherId == data_source.personId
                        ).first()
                        if father_match:
                            sex_value = 0
                        else:
                            mother_match = session.query(Ancestry_matchTrees).filter(
                                Ancestry_matchTrees.motherId == data_source.personId
                            ).first()
                            if mother_match:
                                sex_value = 1

                    unique_id = tree.matchid
                    match_group_data = id_mapping.get(unique_id, {})

                    # Update name and gender based on match_group_data
                    if tree.relid == '1':
                        surname = match_group_data.get('Surname', tree.surname)
                        given = match_group_data.get('Given', tree.given)
                        name_type = match_group_data.get('NameType', 6)
                        sex_value = match_group_data.get('sex', sex_value)

                        # Ensure FatherID and MotherID are included
                        father_id = hash_id(tree.fatherId, id_mapping) if tree.fatherId is not None else father_id
                        mother_id = hash_id(tree.motherId, id_mapping) if tree.motherId is not None else mother_id
                    else:
                        unique_id = generate_unique_id(tree.given, tree.surname, tree.matchid, tree.relid)
                        surname = tree.surname
                        given = tree.given
                        name_type = 2

                    return {
                        'source': 'process_matchtree',
                        'unique_id': unique_id,
                        'sex': sex_value,
                        'color': 24,
                        'matchid': tree.matchid,
                        'Surname': surname,
                        'Given': given,
                        'birthdate': tree.birthdate,
                        'deathdate': tree.deathdate,
                        'birthplace': tree.birthplace,
                        'deathplace': tree.deathplace,
                        'relid': tree.relid,
                        'PersonID': person_id,
                        'FatherID': father_id,
                        'MotherID': mother_id,
                        'DNAProvider': 2,
                        'Date': tree.created_date,
                        'IsPrimary': 1,
                        'NameType': name_type,
                    }

                except ValueError as mte:
                    logging.warning(f"Invalid ID value for tree {tree.matchid}: {str(mte)}. Skipping.")
                    return None

            try:
                # Process match trees with limit and process_matchtree function
                match_trees = batch_limit(
                    session, Ancestry_matchTrees, filtered_ids.get('Ancestry_matchTrees', []),
                    process_matchtree, limit
                )

                # Extend processed ancestry data
                processed_ancestry_data.extend(match_trees or [])
            except Exception as e:
                logging.error(f"An error occurred while processing Ancestry match trees: {str(e)}")
                logging.exception("Exception details:")
                logging.error(traceback.format_exc())

        # Process Ancestry_TreeData data
        if ancestry_treedata and filtered_ids.get('Ancestry_TreeData'):
            def process_treedata(treedata):
                try:
                    return {
                        'source': 'process_treedata',
                        'TestGuid': treedata.TestGuid,
                        'TreeSize': treedata.TreeSize,
                        'PublicTree': treedata.PublicTree,
                        'PrivateTree': treedata.PrivateTree,
                        'UnlinkedTree': treedata.UnlinkedTree,
                        'TreeId': treedata.TreeId,
                        'NoTrees': treedata.NoTrees,
                        'TreeUnavailable': treedata.TreeUnavailable,
                    }
                except AttributeError as tde:
                    logging.warning(f"Missing attribute in tree data: {str(tde)}. Skipping this record.")
                    return None

            try:
                # Process Ancestry tree data
                tree_data = batch_limit(
                    session, Ancestry_TreeData, filtered_ids.get('Ancestry_TreeData', []),
                    process_treedata, limit
                )

                processed_ancestry_data.extend(tree_data or [])
            except Exception as e:
                logging.error(f"An error occurred while processing Ancestry tree data: {str(e)}")
                logging.exception("Exception details:")
                logging.error(traceback.format_exc())

        # Process Ancestry_ICW data
        if ancestry_icw and filtered_ids.get('Ancestry_ICW'):
            def process_icw(icw):
                return {
                    'source': 'process_icw',
                    'matchGuid': icw.matchid,
                    'icwGuid': icw.icwid,
                    'Date': icw.created_date,
                    'sharedCM': icw.sharedCentimorgans,
                    'confidence': icw.confidence,
                    'meiosis': icw.meiosis,
                    'numSharedSegments': icw.numSharedSegments,
                    'DNAProvider': 2,
                }

            try:
                # Process Ancestry ICW data
                icw_data = batch_limit(
                    session, Ancestry_ICW, filtered_ids.get('Ancestry_ICW', []),
                    process_icw, limit
                )

                processed_ancestry_data.extend(icw_data or [])
            except Exception as e:
                logging.error(f"An error occurred while processing Ancestry ICW data: {str(e)}")
                logging.exception("Exception details:")
                logging.error(traceback.format_exc())

        # Process Ancestry_matchEthnicity
        if ancestry_matchethnicity and filtered_ids.get('Ancestry_matchEthnicity'):
            def process_matchethnicity(ethnicity):
                try:
                    return {
                        'source': 'process_matchethnicity',
                        'unique_id': generate_unique_id(ethnicity.matchGuid),
                        'matchGuid': ethnicity.matchGuid,
                        'ethnicregions': ethnicity.ethnicregions,
                        'ethnictraceregions': ethnicity.ethnictraceregions,
                        'Date': ethnicity.created_date,
                        'percent': ethnicity.percent,
                        'version': ethnicity.version,
                    }
                except AttributeError as mee:
                    logging.warning(f"Missing attribute in match ethnicity: {str(mee)}. Skipping this record.")
                    return None

            try:
                # Process Ancestry match ethnicity data
                match_ethnicity_data = batch_limit(
                    session, Ancestry_matchEthnicity, filtered_ids.get('Ancestry_matchEthnicity', []),
                    process_matchethnicity, limit
                )

                processed_ancestry_data.extend(match_ethnicity_data or [])
            except Exception as e:
                logging.error(f"An error occurred while processing Ancestry match ethnicity data: {str(e)}")
                logging.exception("Exception details:")
                logging.error(traceback.format_exc())

        # Process AncestryAncestorCouple
        if ancestry_ancestorcouple and filtered_ids.get('AncestryAncestorCouple'):
            def process_ancestorcouple(couple):
                try:
                    return {
                        'source': 'process_ancestorcouple',
                        'Id': couple.Id,
                        'TestGuid': couple.TestGuid,
                        'MatchGuid': couple.MatchGuid,
                        'FatherAmtGid': couple.FatherAmtGid,
                        'FatherBigTreeGid': couple.FatherBigTreeGid,
                        'FatherKinshipPathToSampleId': couple.FatherKinshipPathToSampleId,
                        'FatherKinshipPathFromSampleToMatch': couple.FatherKinshipPathFromSampleToMatch,
                        'FatherPotential': couple.FatherPotential,
                        'FatherInMatchTree': couple.FatherInMatchTree,
                        'FatherInBestContributorTree': couple.FatherInBestContributorTree,
                        'FatherDisplayName': couple.FatherDisplayName,
                        'FatherBirthYear': couple.FatherBirthYear,
                        'FatherDeathYear': couple.FatherDeathYear,
                        'FatherIsMale': couple.FatherIsMale,
                        'FatherNotFound': couple.FatherNotFound,
                        'FatherVeiled': couple.FatherVeiled,
                        'FatherRelationshipToSampleId': couple.FatherRelationshipToSampleId,
                        'FatherRelationshipFromSampleToMatch': couple.FatherRelationshipFromSampleToMatch,
                        'MotherAmtGid': couple.MotherAmtGid,
                        'MotherBigTreeGid': couple.MotherBigTreeGid,
                        'MotherKinshipPathToSampleId': couple.MotherKinshipPathToSampleId,
                        'MotherKinshipPathFromSampleToMatch': couple.MotherKinshipPathFromSampleToMatch,
                        'MotherPotential': couple.MotherPotential,
                        'MotherInMatchTree': couple.MotherInMatchTree,
                        'MotherInBestContributorTree': couple.MotherInBestContributorTree,
                        'MotherDisplayName': couple.MotherDisplayName,
                        'MotherBirthYear': couple.MotherBirthYear,
                        'MotherDeathYear': couple.MotherDeathYear,
                        'MotherIsFemale': couple.MotherIsFemale,
                        'MotherNotFound': couple.MotherNotFound,
                        'MotherVeiled': couple.MotherVeiled,
                        'MotherRelationshipToSampleId': couple.MotherRelationshipToSampleId,
                        'MotherRelationshipFromSampleToMatch': couple.MotherRelationshipFromSampleToMatch,
                        'date': couple.date,
                    }
                except AttributeError as ace:
                    logging.warning(f"Missing attribute in ancestor couple: {str(ace)}. Skipping this record.")
                    return None

            try:
                # Process Ancestry ancestor couple data
                ancestor_couple_data = batch_limit(
                    session, AncestryAncestorCouple, filtered_ids.get('AncestryAncestorCouple', []),
                    process_ancestorcouple, limit
                )

                processed_ancestry_data.extend(ancestor_couple_data or [])
            except Exception as e:
                logging.error(f"An error occurred while processing Ancestry ancestor couple data: {str(e)}")
                logging.exception("Exception details:")

    except Exception as e:
        logging.error(f"An error occurred during processing Ancestry data: {str(e)}")
        logging.error(traceback.format_exc())

    return processed_ancestry_data


# Process FTDNA data
def process_ftdna(session: Session, filtered_ids):
    global limit
    logging.getLogger('process_ftdna')
    # logging.info("Processing FTDNA data...")

    processed_ftdna_data = []

    try:
        if ftdna_matches2 and filtered_ids.get('FTDNA_Matches2'):
            def process_ftdna_match(match):
                return {
                    'unique_id': generate_unique_id(match.eKit1, match.eKit2),
                    'sex': 1 if match.Female else 0,
                    'color': 26,
                    'Name': match.Name,
                    'MatchPersonName': match.MatchPersonName,
                    'Email': match.Email,
                    'Relationship': match.Relationship,
                    'totalCM': match.totalCM,
                    'longestCentimorgans': match.longestCentimorgans,
                    'yHaplo': match.yHaplo,
                    'mtHaplo': match.mtHaplo,
                }

            processed_ftdna_data.extend(batch_limit(
                session, FTDNA_Matches2, filtered_ids['FTDNA_Matches2'],
                process_ftdna_match, limit
            ))

        if ftdna_chromo2 and filtered_ids.get('FTDNA_Chromo2'):
            def process_ftdna_chromo(chromo):
                return {
                    'unique_id': generate_unique_id(chromo.eKit1, chromo.eKit2, chromo.chromosome),
                    'color': 26,
                    'eKit1': chromo.eKit1,
                    'eKit2': chromo.eKit2,
                    'chromosome': chromo.chromosome,
                    'cmfloat': chromo.cmfloat,
                    'p1': chromo.p1,
                    'p2': chromo.p2,
                    'snpsI': chromo.snpsI,
                }

            processed_ftdna_data.extend(batch_limit(
                session, FTDNA_Chromo2, filtered_ids['FTDNA_Chromo2'],
                process_ftdna_chromo, limit
            ))

        if ftdna_icw2 and filtered_ids.get('FTDNA_ICW2'):
            def process_ftdna_icw(icw):
                return {
                    'unique_id': generate_unique_id(icw.eKitKit, icw.eKitMatch1, icw.eKitMatch2),
                    'color': 26,
                    'eKitKit': icw.eKitKit,
                    'eKitMatch1': icw.eKitMatch1,
                    'eKitMatch2': icw.eKitMatch2,
                }

            processed_ftdna_data.extend(batch_limit(
                session, FTDNA_ICW2, filtered_ids['FTDNA_ICW2'],
                process_ftdna_icw, limit
            ))

        if dg_tree and filtered_ids.get('DGTree'):
            def process_dg_tree(tree):
                return {
                    'unique_id': generate_unique_id(tree.treeid, tree.matchID),
                    'color': 26,
                    'name': tree.name,
                    'treeid': tree.treeid,
                    'treeurl': tree.treeurl,
                    'basePersonId': tree.basePersonId,
                    'matchID': tree.matchID,
                }

            processed_ftdna_data.extend(batch_limit(
                session, DGTree, filtered_ids['DGTree'],
                process_dg_tree, limit
            ))

        if dg_individual and filtered_ids.get('DGIndividual'):
            def process_dg_individual(individual):
                return {
                    'unique_id': generate_unique_id(individual.treeid, individual.matchid, individual.personId),
                    'sex': 1 if individual.sex == 'F' else 0 if individual.sex == 'M' else 2,
                    'color': 26,
                    'treeid': individual.treeid,
                    'matchid': individual.matchid,
                    'surname': individual.surname,
                    'given': individual.given,
                    'birthdate': individual.birthdate,
                    'deathdate': individual.deathdate,
                    'birthplace': individual.birthplace,
                    'deathplace': individual.deathplace,
                    'personId': individual.personId,
                    'fatherId': individual.fatherId,
                    'motherId': individual.motherId,
                }

            processed_ftdna_data.extend(batch_limit(
                session, DGIndividual, filtered_ids['DGIndividual'],
                process_dg_individual, limit
            ))

    except Exception as e:
        logging.error(f"Error processing FTDNA data: {e}")
        logging.error(traceback.format_exc())

    return processed_ftdna_data


# Process MyHeritage data
def process_mh(session: Session, filtered_ids):
    global limit
    logging.getLogger('process_mh')
    # logging.info("Processing MyHeritage data...")

    processed_mh_data = []

    try:
        if mh_match and filtered_ids.get('MH_Match'):
            def process_mh_match(match):
                return {
                    'unique_id': generate_unique_id(match.guid),
                    'sex': 1 if match.gender == 'F' else 0 if match.gender == 'M' else 2,
                    'color': 27,
                    'name': match.name,
                    'first_name': match.first_name,
                    'last_name': match.last_name,
                    'estimated_relationship': match.estimated_relationship,
                    'totalCM': match.totalCM,
                    'percent_shared': match.percent_shared,
                    'num_segments': match.num_segments,
                    'largestCM': match.largestCM,
                    'has_tree': match.has_tree,
                    'tree_size': match.tree_size,
                    'tree_url': match.tree_url,
                }

            processed_mh_data.extend(batch_limit(
                session, MH_Match, filtered_ids['MH_Match'],
                process_mh_match, limit
            ))

        if mh_ancestors and filtered_ids.get('MH_Ancestors'):
            def process_mh_ancestors(ancestor):
                return {
                    'unique_id': generate_unique_id(ancestor.TreeId, ancestor.personId),
                    'sex': 1 if ancestor.gender == 'F' else 0 if ancestor.gender == 'M' else 2,
                    'color': 27,
                    'TreeId': ancestor.TreeId,
                    'matchid': ancestor.matchid,
                    'surname': ancestor.surname,
                    'given': ancestor.given,
                    'birthdate': ancestor.birthdate,
                    'deathdate': ancestor.deathdate,
                    'birthplace': ancestor.birthplace,
                    'deathplace': ancestor.deathplace,
                    'personId': ancestor.personId,
                    'fatherId': ancestor.fatherId,
                    'motherId': ancestor.motherId,
                }

            processed_mh_data.extend(batch_limit(
                session, MH_Ancestors, filtered_ids['MH_Ancestors'],
                process_mh_ancestors, limit
            ))

        if mh_chromo and filtered_ids.get('MH_Chromo'):
            def process_mh_chromo(chromo):
                return {
                    'unique_id': generate_unique_id(chromo.guid, chromo.chromosome, chromo.start),
                    'color': 27,
                    'guid': chromo.guid,
                    'guid1': chromo.guid1,
                    'guid2': chromo.guid2,
                    'chromosome': chromo.chromosome,
                    'cm': chromo.cm,
                    'start': chromo.start,
                    'end': chromo.end,
                    'snps': chromo.snps,
                }

            processed_mh_data.extend(batch_limit(
                session, MH_Chromo, filtered_ids['MH_Chromo'],
                process_mh_chromo, limit
            ))

        if mh_icw and filtered_ids.get('MH_ICW'):
            def process_mh_icw(icw):
                return {
                    'unique_id': generate_unique_id(icw.id1, icw.id2),
                    'color': 27,
                    'id1': icw.id1,
                    'id2': icw.id2,
                    'totalCM': icw.totalCM,
                    'percent_shared': icw.percent_shared,
                    'num_segments': icw.num_segments,
                    'triTotalCM': icw.triTotalCM,
                    'triSegments': icw.triSegments,
                }

            processed_mh_data.extend(batch_limit(
                session, MH_ICW, filtered_ids['MH_ICW'],
                process_mh_icw, limit
            ))

        if mh_tree and filtered_ids.get('MH_Tree'):
            def process_mh_tree(tree):
                return {
                    'unique_id': generate_unique_id(tree.treeurl),
                    'color': 27,
                    'treeurl': tree.treeurl,
                    'Date': tree.created_date,
                    'updated_date': tree.updated_date,
                }

            processed_mh_data.extend(batch_limit(
                session, MH_Tree, filtered_ids['MH_Tree'],
                process_mh_tree, limit
            ))

    except Exception as e:
        logging.error(f"Error processing MyHeritage data: {e}")
        logging.error(traceback.format_exc())

    return processed_mh_data


# Import data into RootsMagic PersonTable.
def insert_person(person_rm_session: Session, processed_data, batch_size=limit):
    logging.getLogger('insert_person')
    # logging.info("Inserting or updating individuals in PersonTable...")

    if person_rm_session is None:
        logging.error("Invalid person_rm_session object provided")
        logging.error(traceback.format_exc())
        raise ValueError("A valid Session object must be provided")

    try:
        processed_count = 0
        blank_record_count = 0
        for data in processed_data:
            if data.get('source') == 'process_icw':
                continue

            person_id = data.get('PersonID')
            relid = data.get('relid')
            unique_id = data.get('unique_id')
            sex_value = data.get('sex', '')

            # logging.debug(f"Processing record: PersonID: {person_id}, "
            #               f"UniqueID: {unique_id}, sex: {sex_value}, relid: {relid}")

            if person_id is None and not unique_id:
                blank_record_count += 1
                logging.warning(f"Potentially problematic record: PersonID: None, "
                                f"UniqueID: None, sex: {sex_value}, relid: {relid}")
                continue  # Skip processing if both PersonID and UniqueID are missing

            person_data = {
                'UniqueID': unique_id,
                'Sex': sex_value,
                'Color': data.get('color', ''),
                'UTCModDate': func.julianday(func.current_timestamp()) - 2415018.5,
            }

            if person_id is not None:
                person_data['PersonID'] = person_id

            existing_person = None
            if person_id is not None:
                existing_person = person_rm_session.query(PersonTable).filter_by(PersonID=person_id).first()
            if not existing_person and unique_id:
                existing_person = person_rm_session.query(PersonTable).filter_by(UniqueID=unique_id).first()

            if existing_person:
                if relid != '1':
                    for key, value in person_data.items():
                        setattr(existing_person, key, value)
                    # logging.debug(f"Updated existing record: PersonID: {person_id}, UniqueID: {unique_id}")
                else:
                    setattr(existing_person, 'UTCModDate', person_data['UTCModDate'])
                    # logging.debug(f"Updated existing record (relid=1): PersonID: {person_id}, UniqueID: {unique_id}")
            else:
                new_person = PersonTable(**person_data)
                person_rm_session.add(new_person)
                # logging.debug(f"Inserted new record: PersonID: {person_id}, UniqueID: {unique_id}")

            processed_count += 1
            if batch_size > 0 and processed_count % batch_size == 0:
                person_rm_session.flush()

        person_rm_session.commit()
        logging.info(f"Processed {processed_count} person records. {blank_record_count} "
                     f"records had neither PersonID nor UniqueID.")

    except Exception as e:
        logging.error(f"Error inserting or updating PersonTable: {e}")
        logging.error(traceback.format_exc())
        person_rm_session.rollback()
        raise

    finally:
        person_rm_session.close()


# Import data into RootsMagic NameTable.
def insert_name(name_rm_session: Session, processed_data, batch_size=limit):
    logging.getLogger('insert_name')
    # logging.info("Inserting or updating names in NameTable...")

    if name_rm_session is None:
        logging.error("Invalid name_rm_session object provided")
        logging.error(traceback.format_exc())
        raise ValueError("A valid Session object must be provided")

    try:
        processed_count = 0
        for data in processed_data:
            if data.get('source') == 'process_icw':
                continue
            # Get PersonID from processed_data
            person_id = data.get('PersonID') or data.get('personId')

            # If person_id is None, try to find it in the PersonTable
            if person_id is None:
                unique_id = data.get('unique_id')
                if unique_id:
                    person_record = name_rm_session.query(PersonTable).filter_by(UniqueID=unique_id).first()
                    if person_record:
                        person_id = person_record.PersonID
                    else:
                        logging.warning(f"No matching PersonID found for UniqueID: {unique_id}")
                else:
                    logging.warning("No PersonID or UniqueID available for this record")

            # Map processed_data to NameTable columns
            name_data = {
                'OwnerID': person_id,
                'Surname': data.get('Surname', ''),
                'Given': data.get('Given', ''),
                'NameType': data.get('NameType', ''),
                'IsPrimary': data.get('IsPrimary', ''),
                'SortDate': int(9223372036854775807),
                'IsPrivate': 0,
                'Proof': 0,
                'SurnameMP': data.get('Surname', ''),
                'GivenMP': data.get('Given', ''),
                'UTCModDate': func.julianday(func.current_timestamp()) - 2415018.5,
            }

            # Check if a name record already exists for this person and name type
            existing_name = None
            if person_id is not None:
                existing_name = name_rm_session.query(NameTable).filter_by(OwnerID=person_id).first()

            if existing_name:
                # Update existing record
                for key, value in name_data.items():
                    setattr(existing_name, key, value)
                # logging.debug(f"Updated name record for OwnerID: {person_id} {name_data}")
            else:
                # Create new record
                new_name = NameTable(**name_data)
                name_rm_session.add(new_name)
                # logging.debug(f"Inserted new name record for OwnerID: {person_id} {name_data}")

            processed_count += 1
            if batch_size > 0 and processed_count % batch_size == 0:
                name_rm_session.flush()

        name_rm_session.commit()
        logging.info(f"Processed {processed_count} name records.")

    except Exception as e:
        logging.error(f"Error inserting or updating NameTable: {e}")
        logging.error(traceback.format_exc())
        name_rm_session.rollback()
        raise

    finally:
        name_rm_session.close()


# Import data into RootsMagic FamilyTable
def insert_family(family_rm_session: Session, processed_data, batch_size=limit):
    logging.getLogger('insert_family')
    # logging.info("Inserting or updating family data in FamilyTable...")

    try:
        processed_count = 0

        for data in processed_data:

            if data.get('source') == 'process_icw':
                continue

            family_id = data.get('FamilyID')
            father_id = data.get('FatherID')
            mother_id = data.get('MotherID')
            child_id = data.get('PersonID')

            # If FamilyID is provided, look for an existing record with that FamilyID
            if family_id:
                existing_family = family_rm_session.query(FamilyTable).filter_by(FamilyID=family_id).first()
            else:
                # If no FamilyID, look for an existing record with matching FatherID, MotherID, and ChildID
                existing_family = family_rm_session.query(FamilyTable).filter(
                    FamilyTable.FatherID == father_id,
                    FamilyTable.MotherID == mother_id,
                    FamilyTable.ChildID == child_id
                ).first()

            if existing_family:
                # Merge new data into the existing record
                for key, value in data.items():
                    if key in FamilyTable.__table__.columns and value is not None:
                        setattr(existing_family, key, value)
                existing_family.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5
                data['FamilyID'] = existing_family.FamilyID  # Update FamilyID in data
            else:
                # Create new record in FamilyTable
                family_data = {
                    'FatherID': father_id,
                    'MotherID': mother_id,
                    'ChildID': child_id,
                    'UTCModDate': func.julianday(func.current_timestamp()) - 2415018.5,
                }
                new_family = FamilyTable(**family_data)
                family_rm_session.add(new_family)
                family_rm_session.flush()  # Ensure the new record is written to the database

                # Retrieve the FamilyID of the new record
                data['FamilyID'] = new_family.FamilyID

            # Update PersonTable with FamilyID as ParentID and SpouseID
            if father_id:
                father = family_rm_session.query(PersonTable).filter_by(PersonID=father_id).first()
                if father:
                    father.SpouseID = data['FamilyID']
                    father.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5

            if mother_id:
                mother = family_rm_session.query(PersonTable).filter_by(PersonID=mother_id).first()
                if mother:
                    mother.SpouseID = data['FamilyID']
                    mother.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5

            child = family_rm_session.query(PersonTable).filter_by(PersonID=child_id).first()
            if child:
                child.ParentID = data['FamilyID']
                child.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5
            else:
                # If no existing person, create new person record
                new_person = PersonTable(
                    PersonID=child_id,
                    ParentID=data['FamilyID'],
                    UTCModDate=func.julianday(func.current_timestamp()) - 2415018.5
                )
                family_rm_session.add(new_person)

            processed_count += 1
            if batch_size > 0 and processed_count % batch_size == 0:
                family_rm_session.flush()

        family_rm_session.commit()
        logging.info(f"Processed {processed_count} family records.")
        return processed_data

    except Exception as e:
        logging.error(f"Error inserting or updating FamilyTable: {e}")
        logging.error(traceback.format_exc())
        family_rm_session.rollback()
        raise

    finally:
        family_rm_session.close()


# Import data into RootsMagic ChildTable
def insert_child(child_rm_session: Session, processed_data, batch_size=limit):
    logging.getLogger('insert_child')
    # logging.info("Inserting or updating children in ChildTable...")

    try:
        processed_count = 0

        for data in processed_data:
            if data.get('source') == 'process_icw':
                continue

            child_id = data.get('PersonID')
            family_id = data.get('FamilyID')

            # Check if both ChildID and FamilyID are present
            if not child_id or not family_id:
                logging.warning(f"Skipped processing record due to missing ChildID or FamilyID: "
                                f"ChildID={child_id}, FamilyID={family_id}")
                continue

            # Check if a child record already exists for the given ChildID and FamilyID
            existing_child = child_rm_session.query(ChildTable).filter_by(
                ChildID=child_id, FamilyID=family_id).first()

            if existing_child:
                # Merge new data into the existing record
                for key, value in data.items():
                    if key in ChildTable.__table__.columns and value is not None:
                        setattr(existing_child, key, value)
                existing_child.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5
                # logging.debug(
                #     f"Updated existing child record for ChildID: {child_id} and FamilyID: {family_id}")
            else:
                # Create new record in ChildTable
                child_data = {
                    'ChildID': child_id,
                    'FamilyID': family_id,
                    'UTCModDate': func.julianday(func.current_timestamp()) - 2415018.5,
                }
                new_child = ChildTable(**child_data)
                child_rm_session.add(new_child)
                # logging.debug(f"Inserted new child record for ChildID: {child_id} and FamilyID: {family_id}")

            processed_count += 1
            if batch_size > 0 and processed_count % batch_size == 0:
                child_rm_session.flush()

        child_rm_session.commit()
        logging.info(f"Processed {processed_count} child records.")

    except Exception as e:
        logging.error(f"Error inserting or updating ChildTable: {e}")
        logging.error(traceback.format_exc())
        child_rm_session.rollback()
        raise
    finally:
        child_rm_session.close()


# Import data into RootsMagic DNATable
def insert_dna(dna_rm_session: Session, processed_data, selected_kits, batch_size=limit):
    logging.getLogger('insert_dna')
    # logging.info("Inserting or updating DNA data in DNATable...")

    try:
        processed_count = 0

        for kit in selected_kits:
            selected_kit_guid = kit[1]
            #  logging.info(f"Processing data for kit GUID: {selected_kit_guid}")

            for data in processed_data:
                if 'source' in data and data['source'] == 'process_matchgroup':
                    person_1 = dna_rm_session.query(PersonTable).filter_by(UniqueID=selected_kit_guid).first()
                    person_id_1 = person_1.PersonID if person_1 else None

                    person_id_2 = data.get('PersonID')

                    label1 = data['testGuid']
                    label2 = data['matchGuid']
                    note = (f"https://www.ancestry.com/discoveryui-matches/compare/"
                            f"{data['testGuid']}/with/{data.get('matchGuid')}")

                elif data['source'] == 'process_icw':
                    match_guid = data['matchGuid']
                    icw_guid = data['icwGuid']

                    person_1 = dna_rm_session.query(PersonTable).filter_by(UniqueID=match_guid).first()
                    person_id_1 = person_1.PersonID if person_1 else None

                    person_2 = dna_rm_session.query(PersonTable).filter_by(UniqueID=icw_guid).first()
                    person_id_2 = person_2.PersonID if person_2 else None

                    label1 = match_guid
                    label2 = icw_guid
                    note = (f"https://www.ancestry.com/discoveryui-matches/compare/"
                            f"{data['matchGuid']}/with/{data.get('icwGuid')}")

                else:
                    continue

                if not person_id_1 or not person_id_2:
                    continue

                shared_cm = data.get('sharedCM')
                date = data.get('Date') or data.get('matchRunDate')

                dna_data = {
                    'ID1': person_id_1,
                    'ID2': person_id_2,
                    'Label1': label1,
                    'Label2': label2,
                    'DNAProvider': data.get('DNAProvider'),
                    'SharedCM': shared_cm,
                    'SharedPercent': round(shared_cm / 69, 2) if shared_cm else None,
                    'SharedSegs': data.get('SharedSegs'),
                    'Date': date,
                    'Note': note,
                    'UTCModDate': func.julianday(func.current_timestamp()) - 2415018.5,
                }

                existing_dna = (dna_rm_session.query(DNATable)
                                .filter(((DNATable.ID1 == person_id_1) & (DNATable.ID2 == person_id_2)) |
                                        ((DNATable.ID1 == person_id_2) & (DNATable.ID2 == person_id_1)))
                                .first())

                if existing_dna:
                    for key, value in dna_data.items():
                        setattr(existing_dna, key, value)
                    existing_dna.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5
                else:
                    new_dna = DNATable(**dna_data)
                    dna_rm_session.add(new_dna)

                processed_count += 1
                if batch_size > 0 and processed_count % batch_size == 0:
                    dna_rm_session.flush()

        dna_rm_session.commit()
        logging.info(f"Processed {processed_count} DNA records.")

    except Exception as e:
        logging.error(f"Error inserting or updating DNATable: {e}")
        logging.error(traceback.format_exc())
        dna_rm_session.rollback()
        raise
    finally:
        dna_rm_session.close()


def insert_events(event_rm_session: Session, processed_data, batch_size=limit):
    logger = logging.getLogger('insert_events')
    # logger.info("Inserting or updating places and events...")

    def transform_date(date_str):
        if not date_str:
            return "."

        date_str = date_str.strip().lower()

        # Check if the date is already in YYYY-MM-DD format
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            year, month, day = date_str.split('-')
            return f"D.+{year}{month}{day}.+00000000.."

        # Define month mapping
        month_map = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
            "may": "05", "jun": "06", "jul": "07", "aug": "08",
            "sep": "09", "oct": "10", "nov": "11", "dec": "12",
            "january": "01", "february": "02", "march": "03", "april": "04",
            "june": "06", "july": "07", "august": "08", "september": "09",
            "october": "10", "november": "11", "december": "12"
        }

        # Regular expressions for different date formats
        full_date_re = r"^(?P<day>\d{1,2}) (?P<month>\w{3,9}) (?P<year>-?\d{1,4})(?: bc)?$"
        month_year_re = r"^(?P<month>\w{3,9}) (?P<year>-?\d{1,4})(?: bc)?$"
        year_only_re = r"^(?P<year>-?\d{1,4})(?: bc)?$"
        day_month_re = r"^(?P<day>\d{1,2}) (?P<month>\w{3,9})$"
        month_only_re = r"^(?P<month>\w{3,9})$"
        between_years_re = (r"^(t?between|bet) (?P<start_year>-?\d{1,4})(?: bc)? "
                            r"(and|-) (?P<end_year>-?\d{1,4})(?: bc)?$")
        double_date_re = r"^(?P<day>\d{1,2}) (?P<month>\w{3,9}) (?P<year>\d{4})/(?P<alt_year>\d{2})$"
        quaker_date_re = r"^(?P<day>\d{1,2})da (?P<month>\d{1,2})mo (?P<year>\d{4})$"

        # Date qualifiers and modifiers
        qualifiers = {
            "abt": "A", "about": "A", "est": "E", "calc": "L", "ca": "C", "say": "S"
        }

        # Directional modifiers
        directional_modifiers = {
            "bef.": "B", "bef": "B", "before": "B", "by": "Y", "to": "T", "until": "U",
            "from": "F", "since": "I", "aft": "A", "after": "A"
        }

        # Qualitative modifiers
        qualitative_modifiers = {
            "cert": "6", "prob": "5", "poss": "4", "lkly": "3", "appar": "2", "prhps": "1", "maybe": "?"
        }

        def format_date(f_year, f_month, f_day, f_bc=False, double_date=False, quaker=False):
            f_year = f_year.zfill(4) if f_year else "0000"
            f_month = f_month.zfill(2) if f_month else "00"
            f_day = f_day.zfill(2) if f_day else "00"

            date_type = "Q" if quaker else "D"
            bc_sign = "-" if f_bc else "+"
            double_date_sign = "/" if double_date else "."

            return f"{date_type}.{bc_sign}{f_year}{f_month}{f_day}{double_date_sign}.+00000000.."

        for qual, code in qualifiers.items():
            if re.match(rf"^{re.escape(qual)}\W", date_str):
                date_str = re.sub(rf"^{re.escape(qual)}\W*", "", date_str).strip()
                date_code = transform_date(date_str)
                return f"{date_code[:12]}{code}{date_code[13:]}"

        for mod, code in directional_modifiers.items():
            if re.match(rf"^{re.escape(mod)}\W", date_str):
                date_str = re.sub(rf"^{re.escape(mod)}\W*", "", date_str).strip()
                date_code = transform_date(date_str)
                return f"{date_code[:1]}{code}{date_code[2:]}"

        for mod, code in qualitative_modifiers.items():
            if re.match(rf"^{re.escape(mod)}\W", date_str):
                date_str = re.sub(rf"^{re.escape(mod)}\W*", "", date_str).strip()
                date_code = transform_date(date_str)
                return f"{date_code[:12]}{code}{date_code[13:]}"

        # Handle full date
        match = re.match(full_date_re, date_str)
        if match:
            day = match.group("day")
            month = month_map.get(match.group("month"), "00")
            year = match.group("year")
            bc = "bc" in date_str
            return format_date(year, month, day, bc)

        # Handle month and year
        match = re.match(month_year_re, date_str)
        if match:
            month = month_map.get(match.group("month"), "00")
            year = match.group("year")
            bc = "bc" in date_str
            return format_date(year, month, None, bc)

        # Handle year only
        match = re.match(year_only_re, date_str)
        if match:
            year = match.group("year")
            bc = "bc" in date_str
            return format_date(year, None, None, bc)

        # Handle day and month only
        match = re.match(day_month_re, date_str)
        if match:
            day = match.group("day")
            month = month_map.get(match.group("month"), "00")
            return format_date(None, month, day)

        # Handle month only
        match = re.match(month_only_re, date_str)
        if match:
            month = month_map.get(match.group("month"), "00")
            return format_date(None, month, None)

        # Handle double dates
        match = re.match(double_date_re, date_str)
        if match:
            day = match.group("day")
            month = month_map.get(match.group("month"), "00")
            year = match.group("year")
            return format_date(year, month, day, double_date=True)

        # Handle Quaker dates
        match = re.match(quaker_date_re, date_str)
        if match:
            day = match.group("day")
            month = match.group("month")
            year = match.group("year")
            return format_date(year, month, day, quaker=True)

        # Handle "between" years
        match = re.match(between_years_re, date_str)
        if match:
            start_year = match.group("start_year")
            end_year = match.group("end_year")
            start_bc = "bc" in date_str.split("and")[0]
            end_bc = "bc" in date_str.split("and")[1]
            start_sign = "-" if start_bc else "+"
            end_sign = "-" if end_bc else "+"
            return f"R.{start_sign}{start_year.zfill(4)}0000..{end_sign}{end_year.zfill(4)}0000.."

        # Default to text date
        return f"T{date_str}"

    try:
        processed_count = 0

        for data in processed_data:
            if data.get('source') == 'process_icw':
                continue
            try:
                if data is None:
                    logger.warning("Encountered None data entry, skipping...")
                    continue

                person_id = data.get('PersonID')
                if person_id is None:
                    logger.warning(f"Missing PersonID in data: {data}")
                    continue

                # Ensure person_id is an integer
                try:
                    person_id = int(person_id)
                except ValueError:
                    logger.warning(f"Invalid PersonID: {person_id}. Skipping this record.")
                    continue

                # Insert or update places
                place_ids = {}
                for place_type in ['birthplace', 'deathplace']:
                    place_name = data.get(place_type)
                    if place_name is None:
                        # logger.warning(f"Missing {place_type} in data: {data}")
                        continue

                    existing_place = event_rm_session.query(PlaceTable).filter_by(Name=place_name).first()

                    if existing_place:
                        existing_place.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5
                        # logger.info(f"Updated existing place record for Name: {place_name}")
                        place_ids[place_type] = existing_place.PlaceID
                    else:
                        new_place = PlaceTable(
                            Name=place_name,
                            PlaceType=0,
                            MasterID=0,
                            fsID=0,
                            anID=0,
                            Latitude=0,
                            Longitude=0,
                            LatLongExact=0,
                            UTCModDate=func.julianday(func.current_timestamp()) - 2415018.5
                        )
                        event_rm_session.add(new_place)
                        event_rm_session.flush()
                        # logger.info(f"Inserted new place record for Name: {place_name}")
                        place_ids[place_type] = new_place.PlaceID

                # Insert or update events
                for event_type in ['birthdate', 'deathdate']:
                    event_type_map = {'birthdate': 1, 'deathdate': 2}
                    raw_event_date = data.get(event_type)
                    if raw_event_date is None:
                        # logger.warning(f"Missing {event_type} in data: {data}")
                        continue

                    event_date = transform_date(raw_event_date)

                    existing_event = event_rm_session.query(EventTable).filter_by(
                        OwnerID=person_id, EventType=event_type_map[event_type]).first()

                    if existing_event:
                        existing_event.Date = event_date
                        existing_event.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5
                        # logger.info(
                        # f"Updated existing event record for OwnerID: "
                        # f"{person_id} and EventType: {event_type_map[event_type]}")
                    else:
                        new_event = EventTable(
                            EventType=event_type_map[event_type],
                            OwnerType=0,
                            OwnerID=person_id,
                            PlaceID=place_ids.get(f"{event_type[:-4]}place", 0),
                            Date=event_date,
                            FamilyID=0,
                            SiteID=0,
                            IsPrimary=0,
                            IsPrivate=0,
                            Proof=0,
                            Status=0,
                            UTCModDate=func.julianday(func.current_timestamp()) - 2415018.5
                        )
                        event_rm_session.add(new_event)
                        # logger.info(
                        # f"Inserted new event record for OwnerID: "
                        # f"{person_id} and EventType: {event_type_map[event_type]}")

                processed_count += 1
                if batch_size > 0 and processed_count % batch_size == 0:
                    event_rm_session.flush()

            except Exception as inner_e:
                logger.error(f"Error processing data {data}: {inner_e}")
                logger.error(traceback.format_exc())

        event_rm_session.commit()
        logger.info(f"Processed {processed_count} event records.")

    except Exception as e:
        logger.error(f"Error inserting or updating EventTable and PlaceTable: {e}")
        logger.error(traceback.format_exc())
        event_rm_session.rollback()
        raise
    finally:
        event_rm_session.close()


# Import data into RootsMagic GroupTable
def insert_group(group_rm_session: Session, processed_data, batch_size=limit):
    logging.getLogger('insert_group')
    # logging.info("Inserting or updating group data in GroupTable...")

    try:
        processed_count = 0

        for data in processed_data:
            # Check if a group record already exists for the given GroupID
            existing_group = group_rm_session.query(GroupTable).filter_by(
                GroupID=data['GroupID']).first()

            if existing_group:
                # Update existing record
                for key, value in data.items():
                    setattr(existing_group, key, value)
                existing_group.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5
                logging.info(f"Updated existing group record for GroupID: {data['GroupID']}")
            else:
                # Create new record in GroupTable
                group_data = {
                    'GroupID': data.get('GroupID', None),
                    'StartID': data.get('StartID', None),
                    'EndID': data.get('EndID', None),
                    'UTCModDate': func.julianday(func.current_timestamp()) - 2415018.5,
                }
                new_group = GroupTable(**group_data)
                group_rm_session.add(new_group)
                logging.info(f"Inserted new group record for GroupID: {data['GroupID']}")

            processed_count += 1
            if batch_size > 0 and processed_count % batch_size == 0:
                group_rm_session.flush()

        group_rm_session.commit()
        logging.info(f"Processed {processed_count} group records.")

    except Exception as e:
        logging.error(f"Error inserting or updating GroupTable: {e}")
        logging.error(traceback.format_exc())
        group_rm_session.rollback()
        raise
    finally:
        group_rm_session.close()


# Import data into RootsMagic URLTable
def insert_url(url_rm_session: Session, processed_data, batch_size=limit):
    logging.getLogger('insert_url')
    # logging.info("Inserting or updating URL data in URLTable...")

    try:
        processed_count = 0

        for data in processed_data:
            # Check if a URL record already exists for the given OwnerType and OwnerID
            existing_url = url_rm_session.query(URLTable).filter_by(
                OwnerType=data['OwnerType'], OwnerID=data['OwnerID']).first()

            if existing_url:
                # Update existing record
                for key, value in data.items():
                    setattr(existing_url, key, value)
                existing_url.UTCModDate = func.julianday(func.current_timestamp()) - 2415018.5
                logging.info(
                    f"Updated existing URL record for OwnerType {data['OwnerType']} and OwnerID {data['OwnerID']}")
            else:
                # Create new record in URLTable
                url_data = {
                    'OwnerType': data.get('OwnerType', None),
                    'OwnerID': data.get('OwnerID', None),
                    'LinkType': data.get('LinkType', None),
                    'Name': data.get('Name', None),
                    'URL': data.get('URL', None),
                    'Note': data.get('Note', None),
                    'UTCModDate': func.julianday(func.current_timestamp()) - 2415018.5,
                }
                new_url = URLTable(**url_data)
                url_rm_session.add(new_url)
                logging.info(f"Inserted new URL record for OwnerType {data['OwnerType']} and OwnerID {data['OwnerID']}")

            processed_count += 1
            if batch_size > 0 and processed_count % batch_size == 0:
                url_rm_session.flush()

        url_rm_session.commit()
        logging.info(f"Processed {processed_count} URL records.")

    except Exception as e:
        logging.error(f"Error inserting or updating URLTable: {e}")
        logging.error(traceback.format_exc())
        url_rm_session.rollback()
        raise
    finally:
        url_rm_session.close()


def rebuild_all_indexes(engine):
    inspector = inspect(engine)

    tables_indexes = [
        (ChildTable, ['idxChildOrder', 'idxChildID', 'idxChildFamilyID']),
        (DNATable, ['idxDnaId2', 'idxDnaId1']),
        (EventTable, ['idxOwnerEvent', 'idxOwnerDate']),
        (FactTypeTable, ['idxFactTypeName', 'idxFactTypeAbbrev', 'idxFactTypeGedcomTag']),
        (FamilyTable, ['idxFamilyMotherID', 'idxFamilyFatherID']),
        (NameTable,
         ['idxSurnameGiven', 'idxSurnameGivenMP', 'idxNamePrimary', 'idxGivenMP', 'idxNameOwnerID', 'idxGiven',
          'idxSurname', 'idxSurnameMP']),
        (PlaceTable, ['idxPlaceName', 'idxPlaceAbbrev', 'idxReversePlaceName']),
        (URLTable, ['idxUrlOwnerID', 'idxUrlOwnerType']),
    ]

    with engine.begin() as conn:
        for table, index_names in tables_indexes:
            table_name = table.__tablename__
            # print(f"Processing table: {table_name}")

            # Drop all existing indexes for this table
            existing_indexes = inspector.get_indexes(table_name)
            for idx in existing_indexes:
                if idx['name'] in index_names:
                    conn.execute(text(f"DROP INDEX IF EXISTS {idx['name']}"))
                    # print(f"Dropped index {idx['name']} from {table_name}")

            # Reindex the table
            if engine.dialect.name == 'sqlite':
                # For SQLite, the REINDEX command is used without specifying a table
                conn.execute(text("REINDEX"))
                # print(f"Reindexed all tables (SQLite)")
            else:
                # For other databases, specify the table
                conn.execute(text(f"REINDEX TABLE {table_name}"))
                # print(f"Reindexed table {table_name}")

            # Recreate the indexes
            for index_name in index_names:
                index = next((idx for idx in table.__table__.indexes if idx.name == index_name), None)
                if index:
                    create_idx = CreateIndex(index)
                    conn.execute(create_idx)
                    # print(f"Recreated index {index_name} for table {table_name}")
                else:
                    print(f"Warning: Index {index_name} not found for table {table_name}")

            # Analyze the table
            if engine.dialect.name != 'sqlite':
                conn.execute(text(f"ANALYZE {table_name}"))
                # print(f"Analyzed table {table_name}")

    # print("All indexes rebuilt and tables reindexed successfully")


def main():
    setup_logging()
    logging.info("Connecting to databases...")
    dnagedcom_db_path, rootsmagic_db_path = find_database_paths()

    # Connect to DNAGedcom and RootsMagic databases using SQLAlchemy
    dg_session, dg_engine, rm_session, rm_engine = connect_to_db_sqlalchemy(dnagedcom_db_path, rootsmagic_db_path)

    if not all([dg_session, dg_engine, rm_session, rm_engine]):
        logging.critical("Failed to connect to one or both databases using SQLAlchemy.")
        return

    # logging.info("Fetching user kit data...")
    dna_kits = user_kit_data(dg_session)

    if dna_kits:
        # logging.info("Prompting user for kits...")
        selected_kits = prompt_user_for_kits(dna_kits)

        logging.info("Selected kits:")
        for kit in selected_kits:
            logging.info(f"Type: {kit[0]}, GUID: {kit[1]}, Name: {kit[2]} {kit[3]}")

        filtered_ids = filter_selected_kits(dg_session, selected_kits)
        import_profiles(rm_session, selected_kits)

        # Overall progress bar
        with tqdm(total=11, desc="Overall Progress") as pbar:
            try:
                logging.info("Processing Ancestry data...")
                processed_ancestry_data = process_ancestry(dg_session, filtered_ids)
                pbar.update(1)

                logging.info("Processing FTDNA data...")
                processed_ftdna_data = process_ftdna(dg_session, filtered_ids)
                pbar.update(1)

                logging.info("Processing MyHeritage data...")
                processed_mh_data = process_mh(dg_session, filtered_ids)
                pbar.update(1)

                processed_data = processed_ancestry_data + processed_ftdna_data + processed_mh_data

                # logging.info("Inserting fact types...")
                insert_fact_type(rm_session)
                pbar.update(1)

                logging.info("Inserting persons...")
                insert_person(rm_session, processed_data)
                pbar.update(1)

                logging.info("Inserting names...")
                insert_name(rm_session, processed_data)
                pbar.update(1)

                logging.info("Inserting families...")
                insert_family(rm_session, processed_data)
                pbar.update(1)

                logging.info("Inserting children...")
                insert_child(rm_session, processed_data)
                pbar.update(1)

                logging.info("Inserting DNA records...")
                insert_dna(rm_session, processed_data, selected_kits)
                pbar.update(1)

                logging.info("Inserting events...")
                insert_events(rm_session, processed_data)
                pbar.update(1)

                logging.info("Rebuilding all indexes...")
                rebuild_all_indexes(rm_engine)
                pbar.update(1)
            except Exception as e:
                logging.error(f"Error during data insertion: {e}")
                logging.error(traceback.format_exc())
    else:
        logging.warning("No kits found.")

    # Close sessions and engines
    dg_session.close()
    dg_engine.dispose()
    rm_session.close()
    rm_engine.dispose()


if __name__ == "__main__":
    main()
